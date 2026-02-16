from __future__ import annotations

import json
import logging

import anthropic

from config import Config
from models import Analysis, Post
from taxonomy import get_taxonomy_text

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You analyze and classify social media posts from political figures.

Given one or more posts, treat them as a single batch and produce ONE JSON object (not an array) with exactly these fields:
- "is_economic": boolean — true if the post is primarily about economic/financial topics
- "primary_category": string — the best-matching category from the taxonomy below
- "subcategory": string or null — for economic posts, the best-matching subcategory; null for non-economic
- "secondary_category": string or null — a second relevant category if the post spans multiple topics
- "market_sentiment": "bullish", "bearish", or "neutral" — only for economic posts; null for non-economic
- "confidence": float from 0.0 to 1.0 — how confident you are in the classification
- "summary": a single concise sentence summarizing the key point (under 150 characters)
- "topics": list of 1-3 topic hashtag strings (without the # symbol)
- "relevance_score": float from 0.0 to 1.0 rating newsworthiness

TOPIC TAXONOMY:
{taxonomy}

Classification rules:
1. First determine if the post is primarily economic or non-economic
2. For economic posts: pick the best primary_category from ECONOMIC CATEGORIES, and the best subcategory within it
3. For non-economic posts: pick the best primary_category from NON-ECONOMIC CATEGORIES, set subcategory to null
4. If the post spans two topics, set secondary_category to the second-best category
5. market_sentiment is only for economic posts — set to null for non-economic

Respond with ONLY valid JSON, no markdown formatting."""


class PostAnalyzer:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    def analyze(self, posts: list[Post]) -> Analysis | None:
        if not posts:
            return None

        post_texts = "\n---\n".join(
            f"[{p.platform}] ({p.timestamp})\n{p.content}" for p in posts
        )
        prompt = f"Analyze these social media posts:\n\n{post_texts}"
        system = SYSTEM_PROMPT.format(taxonomy=get_taxonomy_text())

        try:
            response = self.client.messages.create(
                model=self.config.claude_model,
                max_tokens=1500,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1]  # remove opening ```json
                raw = raw.rsplit("```", 1)[0]  # remove closing ```
                raw = raw.strip()
            data = json.loads(raw)
            if isinstance(data, list):
                data = data[0]

            relevance = float(data["relevance_score"])
            if relevance < self.config.min_relevance_score:
                logger.info("Relevance %.2f below threshold, skipping", relevance)
                return None

            is_economic = data.get("is_economic")
            subcategory = data.get("subcategory")
            if is_economic and subcategory is None:
                logger.warning("Economic post has null subcategory: %s", data.get("primary_category"))

            return Analysis(
                summary=data["summary"],
                topics=data["topics"],
                relevance_score=relevance,
                original_posts=posts,
                is_economic=is_economic,
                primary_category=data.get("primary_category"),
                subcategory=subcategory,
                secondary_category=data.get("secondary_category"),
                market_sentiment=data.get("market_sentiment"),
                confidence=data.get("confidence"),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("Failed to parse Claude response: %s", e)
            return None
        except anthropic.APIError as e:
            logger.error("Anthropic API error: %s", e)
            return None
