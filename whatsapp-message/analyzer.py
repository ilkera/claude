from __future__ import annotations

import json
import logging

import anthropic

from config import Config
from models import Analysis, Post

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You analyze social media posts from political figures.
Given a batch of posts, produce a JSON response with exactly these fields:
- "summary": list of 2-4 bullet point strings (each under 100 characters)
- "topics": list of 1-3 topic hashtag strings (without the # symbol)
- "relevance_score": float from 0.0 to 1.0 rating newsworthiness

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

        try:
            response = self.client.messages.create(
                model=self.config.claude_model,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            data = json.loads(raw)

            relevance = float(data["relevance_score"])
            if relevance < self.config.min_relevance_score:
                logger.info("Relevance %.2f below threshold, skipping", relevance)
                return None

            return Analysis(
                summary=data["summary"],
                topics=data["topics"],
                relevance_score=relevance,
                original_posts=posts,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error("Failed to parse Claude response: %s", e)
            return None
        except anthropic.APIError as e:
            logger.error("Anthropic API error: %s", e)
            return None
