from __future__ import annotations

import logging

from dateutil import parser as dateparser

from models import Post

logger = logging.getLogger(__name__)


class PostParser:
    def parse(self, raw_posts: list[dict]) -> list[Post]:
        """Parse raw API post dicts into Post objects."""
        posts: list[Post] = []
        for raw in raw_posts:
            post = self._extract_post(raw)
            if post:
                posts.append(post)
        logger.info("Parsed %d valid posts from %d raw entries", len(posts), len(raw_posts))
        return posts

    def _extract_post(self, raw: dict) -> Post | None:
        content = (raw.get("text") or "").strip()
        if not content:
            return None

        # Timestamp
        timestamp = ""
        raw_date = raw.get("date", "")
        if raw_date:
            try:
                dt = dateparser.parse(raw_date)
                timestamp = dt.isoformat() if dt else raw_date
            except (ValueError, OverflowError):
                timestamp = raw_date

        # Platform detection from document_id or image_url patterns
        platform = self._detect_platform(raw)

        # Image
        image_urls = []
        img = raw.get("image_url", "")
        if img:
            image_urls.append(img)

        return Post(
            platform=platform,
            content=content,
            timestamp=timestamp,
            image_urls=image_urls,
            source_url=raw.get("url", ""),
        )

    def _detect_platform(self, raw: dict) -> str:
        img = raw.get("image_url", "").lower()
        doc_id = raw.get("document_id", "")

        if "truthsocial" in img or "truth" in img:
            return "truth_social"
        if "twitter" in img or "tweet" in img:
            return "twitter"
        # Truth Social document IDs tend to be longer numeric strings
        # Default to truth_social as it's the primary platform now
        return "truth_social"
