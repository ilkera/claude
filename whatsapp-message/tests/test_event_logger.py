from __future__ import annotations

import json

from event_logger import EventLogger, MAX_EVENTS


def test_log_appends_valid_jsonl(tmp_path):
    path = str(tmp_path / "events.jsonl")
    logger = EventLogger(path)
    logger.log("service_start")
    logger.log("poll_end", posts_found=5, new_posts=2, duration_ms=1200)

    with open(path) as f:
        lines = f.readlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["event_type"] == "service_start"
    assert "timestamp" in first

    second = json.loads(lines[1])
    assert second["event_type"] == "poll_end"
    assert second["posts_found"] == 5
    assert second["new_posts"] == 2
    assert second["duration_ms"] == 1200


def test_log_creates_file_on_first_write(tmp_path):
    path = str(tmp_path / "new_events.jsonl")
    logger = EventLogger(path)
    logger.log("service_start")

    with open(path) as f:
        lines = f.readlines()
    assert len(lines) == 1


def test_rotation_caps_at_max_events(tmp_path):
    path = str(tmp_path / "events.jsonl")
    logger = EventLogger(path)

    # Write MAX_EVENTS + 50 entries
    for i in range(MAX_EVENTS + 50):
        logger.log("poll_start")

    with open(path) as f:
        lines = f.readlines()
    assert len(lines) == MAX_EVENTS


def test_log_extra_kwargs(tmp_path):
    path = str(tmp_path / "events.jsonl")
    logger = EventLogger(path)
    logger.log("error", error_type="ValueError", message="something broke")

    with open(path) as f:
        entry = json.loads(f.readline())
    assert entry["error_type"] == "ValueError"
    assert entry["message"] == "something broke"
