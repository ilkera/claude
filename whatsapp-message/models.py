from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


@dataclass
class Post:
    platform: str
    content: str
    timestamp: str
    image_urls: list[str] = field(default_factory=list)
    source_url: str = ""
    post_id: str = ""

    def __post_init__(self) -> None:
        if not self.post_id:
            raw = f"{self.platform}{self.timestamp}{self.content[:100]}"
            self.post_id = hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class Analysis:
    summary: list[str]
    topics: list[str]
    relevance_score: float
    original_posts: list[Post] = field(default_factory=list)
