"""Tests for Issue #3: Ordered eviction and file locking in state.py.

These tests verify that:
- When seen_ids exceeds MAX_SEEN_IDS, the OLDEST entries are evicted (not random)
- File locking prevents corruption from concurrent access

Tests are behavior-focused: they check observable outcomes, not internal
data structures (set vs list vs OrderedDict).
"""
from __future__ import annotations

import json
import multiprocessing
import os
import time
from pathlib import Path

from models import Post
from state import MAX_SEEN_IDS, StateManager


def _make_post(content: str, ts: str = "2026-01-01") -> Post:
    return Post(platform="truth_social", content=content, timestamp=ts)


# ---------------------------------------------------------------------------
# Ordered eviction: newest posts must survive, oldest must be evicted
# ---------------------------------------------------------------------------


class TestOrderedEviction:
    def test_newest_posts_survive_eviction(self, tmp_path):
        """After exceeding MAX_SEEN_IDS, the newest posts must still be seen."""
        sm = StateManager(str(tmp_path / "state.json"))

        # Fill up to the limit
        old_posts = [_make_post(f"old_{i}") for i in range(MAX_SEEN_IDS)]
        sm.mark_seen(old_posts)

        # Add 100 new posts, exceeding the limit
        new_posts = [_make_post(f"new_{i}") for i in range(100)]
        sm.mark_seen(new_posts)

        # Reload from disk to verify persistence
        sm2 = StateManager(str(tmp_path / "state.json"))

        # ALL new posts must be recognized as seen (not evicted)
        assert sm2.filter_new(new_posts) == [], (
            "Newest posts should never be evicted — they must survive the cap"
        )

    def test_oldest_posts_are_evicted(self, tmp_path):
        """After exceeding MAX_SEEN_IDS, the oldest posts should be evicted."""
        sm = StateManager(str(tmp_path / "state.json"))

        # Add old posts first
        old_posts = [_make_post(f"old_{i}") for i in range(MAX_SEEN_IDS)]
        sm.mark_seen(old_posts)

        # Add new posts to exceed the cap
        new_posts = [_make_post(f"new_{i}") for i in range(200)]
        sm.mark_seen(new_posts)

        # Reload from disk
        sm2 = StateManager(str(tmp_path / "state.json"))

        # At least some of the oldest posts should have been evicted
        evicted = sm2.filter_new(old_posts[:200])
        assert len(evicted) > 0, (
            "Some of the oldest posts should have been evicted to make room"
        )

    def test_eviction_is_deterministic(self, tmp_path):
        """Eviction must be deterministic (insertion-order based), not random.

        Running the same sequence twice must evict the same posts.
        """
        results = []
        for run in range(2):
            state_file = str(tmp_path / f"state_run{run}.json")
            sm = StateManager(state_file)

            posts = [_make_post(f"post_{i}") for i in range(MAX_SEEN_IDS + 200)]
            sm.mark_seen(posts)

            sm2 = StateManager(state_file)
            surviving = [p for p in posts if sm2.filter_new([p]) == []]
            results.append(set(p.post_id for p in surviving))

        assert results[0] == results[1], (
            "Eviction should be deterministic — same input should evict same posts"
        )

    def test_cap_still_enforced(self, tmp_path):
        """The MAX_SEEN_IDS cap must still be enforced."""
        sm = StateManager(str(tmp_path / "state.json"))
        posts = [_make_post(f"post_{i}") for i in range(MAX_SEEN_IDS + 500)]
        sm.mark_seen(posts)

        data = json.loads((tmp_path / "state.json").read_text())
        stored_ids = data.get("seen_ids", [])
        assert len(stored_ids) <= MAX_SEEN_IDS, (
            f"Stored IDs ({len(stored_ids)}) should not exceed MAX_SEEN_IDS ({MAX_SEEN_IDS})"
        )


# ---------------------------------------------------------------------------
# File locking: concurrent access should not corrupt the state file
# ---------------------------------------------------------------------------


def _concurrent_writer(state_file: str, prefix: str, count: int):
    """Worker function that marks posts as seen in a separate process."""
    sm = StateManager(state_file)
    posts = [_make_post(f"{prefix}_{i}") for i in range(count)]
    for post in posts:
        sm.mark_seen([post])


class TestFileLocking:
    def test_concurrent_writes_produce_valid_json(self, tmp_path):
        """Multiple processes writing concurrently should not corrupt the file."""
        state_file = str(tmp_path / "state.json")

        # Initialize the file
        sm = StateManager(state_file)
        sm.mark_seen([_make_post("init")])

        # Run concurrent writers
        procs = []
        for i in range(3):
            p = multiprocessing.Process(
                target=_concurrent_writer,
                args=(state_file, f"proc{i}", 20),
            )
            procs.append(p)
            p.start()

        for p in procs:
            p.join(timeout=30)

        # The file must still be valid JSON after concurrent writes
        content = Path(state_file).read_text()
        data = json.loads(content)  # should not raise
        assert "seen_ids" in data
        assert isinstance(data["seen_ids"], list)
        assert len(data["seen_ids"]) > 0

    def test_concurrent_writes_no_data_loss(self, tmp_path):
        """Posts marked as seen should not be lost due to concurrent access."""
        state_file = str(tmp_path / "state.json")

        # Pre-seed with known posts
        sm = StateManager(state_file)
        seed_posts = [_make_post(f"seed_{i}") for i in range(10)]
        sm.mark_seen(seed_posts)

        # Run a concurrent writer
        p = multiprocessing.Process(
            target=_concurrent_writer,
            args=(state_file, "concurrent", 10),
        )
        p.start()
        p.join(timeout=30)

        # The seed posts should still be seen (not overwritten)
        sm2 = StateManager(state_file)
        still_seen = [post for post in seed_posts if sm2.filter_new([post]) == []]
        assert len(still_seen) == len(seed_posts), (
            "Pre-existing seen posts should not be lost due to concurrent writes"
        )
