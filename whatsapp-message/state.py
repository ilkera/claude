from __future__ import annotations

import json
import logging
from pathlib import Path

from models import Post

logger = logging.getLogger(__name__)

MAX_SEEN_IDS = 5000


class StateManager:
    def __init__(self, state_file: str = "seen_posts.json") -> None:
        self.path = Path(state_file)
        self.seen_ids: set[str] = self._load()

    def _load(self) -> set[str]:
        if not self.path.exists():
            return set()
        try:
            data = json.loads(self.path.read_text())
            return set(data.get("seen_ids", []))
        except (json.JSONDecodeError, TypeError, KeyError):
            logger.warning("Corrupted state file, starting fresh")
            return set()

    def _save(self) -> None:
        ids = list(self.seen_ids)
        if len(ids) > MAX_SEEN_IDS:
            ids = ids[-MAX_SEEN_IDS:]
            self.seen_ids = set(ids)
        self.path.write_text(json.dumps({"seen_ids": ids}))

    def filter_new(self, posts: list[Post]) -> list[Post]:
        return [p for p in posts if p.post_id not in self.seen_ids]

    def mark_seen(self, posts: list[Post]) -> None:
        for p in posts:
            self.seen_ids.add(p.post_id)
        self._save()
