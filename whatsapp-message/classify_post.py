#!/usr/bin/env python3
"""Standalone CLI to classify a Trump social media post using the taxonomy.

Usage: python classify_post.py "post text here"
"""
from __future__ import annotations

import json
import sys

import anthropic

from config import Config
from taxonomy import get_taxonomy_text

SYSTEM_PROMPT = """You classify social media posts from political figures.

Given a post, classify it and produce ONE JSON object with exactly these fields:
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


def classify(post_text: str) -> dict:
    config = Config()
    client = anthropic.Anthropic(api_key=config.anthropic_api_key)
    system = SYSTEM_PROMPT.format(taxonomy=get_taxonomy_text())

    response = client.messages.create(
        model=config.claude_model,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": f"Classify this post:\n\n{post_text}"}],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]
        raw = raw.strip()
    data = json.loads(raw)
    if isinstance(data, list):
        data = data[0]
    return data


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python classify_post.py \"post text\"", file=sys.stderr)
        sys.exit(1)
    post_text = " ".join(sys.argv[1:])
    result = classify(post_text)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
