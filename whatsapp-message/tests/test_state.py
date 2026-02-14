from __future__ import annotations

import json

from models import Post
from state import StateManager, MAX_SEEN_IDS


def _make_post(content: str) -> Post:
    return Post(platform="truth_social", content=content, timestamp="2026-01-01")


def test_filter_new_all_new(tmp_path):
    sm = StateManager(str(tmp_path / "state.json"))
    posts = [_make_post("post1"), _make_post("post2")]
    assert sm.filter_new(posts) == posts


def test_filter_new_some_seen(tmp_path):
    sm = StateManager(str(tmp_path / "state.json"))
    posts = [_make_post("post1"), _make_post("post2")]
    sm.mark_seen([posts[0]])
    new = sm.filter_new(posts)
    assert len(new) == 1
    assert new[0].content == "post2"


def test_filter_new_all_seen(tmp_path):
    sm = StateManager(str(tmp_path / "state.json"))
    posts = [_make_post("post1")]
    sm.mark_seen(posts)
    assert sm.filter_new(posts) == []


def test_persistence_across_instances(tmp_path):
    path = str(tmp_path / "state.json")
    sm1 = StateManager(path)
    posts = [_make_post("post1")]
    sm1.mark_seen(posts)

    sm2 = StateManager(path)
    assert sm2.filter_new(posts) == []


def test_corrupted_file_recovery(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("not valid json!!!")
    sm = StateManager(str(path))
    assert len(sm.seen_ids) == 0


def test_cap_enforcement(tmp_path):
    sm = StateManager(str(tmp_path / "state.json"))
    posts = [_make_post(f"post{i}") for i in range(MAX_SEEN_IDS + 500)]
    sm.mark_seen(posts)
    assert len(sm.seen_ids) == MAX_SEEN_IDS

    # Verify file also capped
    data = json.loads((tmp_path / "state.json").read_text())
    assert len(data["seen_ids"]) == MAX_SEEN_IDS
