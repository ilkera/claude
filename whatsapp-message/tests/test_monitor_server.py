from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from monitor_server import poll_success_rate, read_all_events, read_events


def _make_event(event_type: str, timestamp: datetime, **kwargs: object) -> dict:
    return {
        "event_type": event_type,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        **kwargs,
    }


def _write_events(path: str, events: list[dict]) -> None:
    with open(path, "w") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")


# ---------------------------------------------------------------------------
# read_all_events / read_events
# ---------------------------------------------------------------------------


def test_read_all_events_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("monitor_server.EVENTS_FILE", str(tmp_path / "nope.json"))
    assert read_all_events() == []


def test_read_all_events_chronological(tmp_path, monkeypatch):
    path = str(tmp_path / "events.json")
    now = datetime.now(timezone.utc)
    events = [
        _make_event("poll_end", now - timedelta(minutes=10)),
        _make_event("poll_end", now - timedelta(minutes=5)),
        _make_event("error", now),
    ]
    _write_events(path, events)
    monkeypatch.setattr("monitor_server.EVENTS_FILE", path)

    result = read_all_events()
    assert len(result) == 3
    assert result[0]["event_type"] == "poll_end"
    assert result[2]["event_type"] == "error"


def test_read_events_newest_first(tmp_path, monkeypatch):
    path = str(tmp_path / "events.json")
    now = datetime.now(timezone.utc)
    events = [
        _make_event("poll_end", now - timedelta(minutes=10)),
        _make_event("error", now),
    ]
    _write_events(path, events)
    monkeypatch.setattr("monitor_server.EVENTS_FILE", path)

    result = read_events(limit=10)
    assert result[0]["event_type"] == "error"
    assert result[1]["event_type"] == "poll_end"


# ---------------------------------------------------------------------------
# poll_success_rate — structure
# ---------------------------------------------------------------------------


def test_returns_24_hourly_slots():
    with patch("monitor_server.read_all_events", return_value=[]):
        result = poll_success_rate()
    assert len(result) == 24
    for slot in result:
        assert set(slot.keys()) == {"hour", "success", "failed", "total", "rate"}


def test_empty_log_all_rates_null():
    with patch("monitor_server.read_all_events", return_value=[]):
        result = poll_success_rate()
    for slot in result:
        assert slot["rate"] is None
        assert slot["total"] == 0


# ---------------------------------------------------------------------------
# poll_success_rate — success counting
# ---------------------------------------------------------------------------


def test_poll_end_counted_as_success():
    """poll_end events increment the success counter for their hour."""
    now = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    events = [
        _make_event("poll_end", now - timedelta(minutes=20), posts_found=3),
        _make_event("poll_end", now - timedelta(minutes=10), posts_found=1),
    ]
    with (
        patch("monitor_server.read_all_events", return_value=events),
        patch("monitor_server.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = poll_success_rate()

    # The 14:00 hour slot should have 2 successes
    slot_14 = next(s for s in result if s["hour"].startswith("2026-02-15T14"))
    assert slot_14["success"] == 2
    assert slot_14["failed"] == 0
    assert slot_14["total"] == 2
    assert slot_14["rate"] == 1.0


# ---------------------------------------------------------------------------
# poll_success_rate — error counting
# ---------------------------------------------------------------------------


def test_error_counted_as_failure():
    """error events (including timeouts) increment the failed counter."""
    now = datetime(2026, 2, 15, 14, 30, 0, tzinfo=timezone.utc)
    events = [
        _make_event("error", now - timedelta(minutes=25),
                     error_type="TimeoutError", message="Page.goto: Timeout 60000ms exceeded"),
        _make_event("error", now - timedelta(minutes=15),
                     error_type="ConnectionError", message="Connection refused"),
        _make_event("error", now - timedelta(minutes=5),
                     error_type="ValueError", message="Invalid JSON"),
    ]
    with (
        patch("monitor_server.read_all_events", return_value=events),
        patch("monitor_server.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = poll_success_rate()

    slot_14 = next(s for s in result if s["hour"].startswith("2026-02-15T14"))
    assert slot_14["success"] == 0
    assert slot_14["failed"] == 3
    assert slot_14["total"] == 3
    assert slot_14["rate"] == 0.0


def test_timeout_errors_are_failures():
    """Timeout errors specifically are counted as failures, not ignored."""
    now = datetime(2026, 2, 15, 10, 15, 0, tzinfo=timezone.utc)
    events = [
        _make_event("error", now - timedelta(minutes=10),
                     error_type="TimeoutError",
                     message="Page.goto: Timeout 60000ms exceeded"),
    ]
    with (
        patch("monitor_server.read_all_events", return_value=events),
        patch("monitor_server.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = poll_success_rate()

    slot_10 = next(s for s in result if s["hour"].startswith("2026-02-15T10"))
    assert slot_10["failed"] == 1
    assert slot_10["rate"] == 0.0


# ---------------------------------------------------------------------------
# poll_success_rate — mixed success and error
# ---------------------------------------------------------------------------


def test_mixed_success_and_errors():
    """Rate is correctly computed with both successes and failures in one hour."""
    now = datetime(2026, 2, 15, 20, 45, 0, tzinfo=timezone.utc)
    events = [
        _make_event("poll_end", now - timedelta(minutes=40)),
        _make_event("poll_end", now - timedelta(minutes=30)),
        _make_event("poll_end", now - timedelta(minutes=20)),
        _make_event("error", now - timedelta(minutes=10),
                     error_type="TimeoutError", message="timeout"),
    ]
    with (
        patch("monitor_server.read_all_events", return_value=events),
        patch("monitor_server.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = poll_success_rate()

    slot_20 = next(s for s in result if s["hour"].startswith("2026-02-15T20"))
    assert slot_20["success"] == 3
    assert slot_20["failed"] == 1
    assert slot_20["total"] == 4
    assert slot_20["rate"] == pytest.approx(0.75)


# ---------------------------------------------------------------------------
# poll_success_rate — multi-hour bucketing
# ---------------------------------------------------------------------------


def test_events_bucketed_into_correct_hours():
    """Events in different hours land in different slots."""
    now = datetime(2026, 2, 15, 16, 30, 0, tzinfo=timezone.utc)
    events = [
        _make_event("poll_end", datetime(2026, 2, 15, 14, 10, tzinfo=timezone.utc)),
        _make_event("error", datetime(2026, 2, 15, 14, 50, tzinfo=timezone.utc),
                     error_type="TimeoutError", message="timeout"),
        _make_event("poll_end", datetime(2026, 2, 15, 15, 5, tzinfo=timezone.utc)),
        _make_event("poll_end", datetime(2026, 2, 15, 15, 35, tzinfo=timezone.utc)),
        _make_event("poll_end", datetime(2026, 2, 15, 16, 10, tzinfo=timezone.utc)),
    ]
    with (
        patch("monitor_server.read_all_events", return_value=events),
        patch("monitor_server.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = poll_success_rate()

    slot_14 = next(s for s in result if s["hour"].startswith("2026-02-15T14"))
    assert slot_14["success"] == 1
    assert slot_14["failed"] == 1
    assert slot_14["rate"] == pytest.approx(0.5)

    slot_15 = next(s for s in result if s["hour"].startswith("2026-02-15T15"))
    assert slot_15["success"] == 2
    assert slot_15["failed"] == 0
    assert slot_15["rate"] == 1.0

    slot_16 = next(s for s in result if s["hour"].startswith("2026-02-15T16"))
    assert slot_16["success"] == 1
    assert slot_16["failed"] == 0
    assert slot_16["rate"] == 1.0


# ---------------------------------------------------------------------------
# poll_success_rate — edge cases
# ---------------------------------------------------------------------------


def test_events_older_than_24h_excluded():
    """Events before the 24h window are not counted."""
    now = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
    old_event = _make_event("poll_end", now - timedelta(hours=25))
    with (
        patch("monitor_server.read_all_events", return_value=[old_event]),
        patch("monitor_server.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = poll_success_rate()

    assert all(s["total"] == 0 for s in result)


def test_non_poll_events_ignored():
    """Only poll_end and error events affect the rate; others are ignored."""
    now = datetime(2026, 2, 15, 10, 30, 0, tzinfo=timezone.utc)
    events = [
        _make_event("service_start", now - timedelta(minutes=20)),
        _make_event("poll_start", now - timedelta(minutes=15)),
        _make_event("notification_sent", now - timedelta(minutes=10)),
        _make_event("notification_skipped", now - timedelta(minutes=5)),
    ]
    with (
        patch("monitor_server.read_all_events", return_value=events),
        patch("monitor_server.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = poll_success_rate()

    assert all(s["total"] == 0 for s in result)
    assert all(s["rate"] is None for s in result)


def test_malformed_timestamp_skipped():
    """Events with unparseable timestamps are silently skipped."""
    now = datetime(2026, 2, 15, 10, 30, 0, tzinfo=timezone.utc)
    events = [
        {"event_type": "poll_end", "timestamp": "not-a-date"},
        {"event_type": "error", "timestamp": ""},
        _make_event("poll_end", now - timedelta(minutes=5)),
    ]
    with (
        patch("monitor_server.read_all_events", return_value=events),
        patch("monitor_server.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = poll_success_rate()

    slot_10 = next(s for s in result if s["hour"].startswith("2026-02-15T10"))
    assert slot_10["success"] == 1
    assert slot_10["failed"] == 0


def test_hour_slots_ordered_oldest_first():
    """The 24 slots are returned in chronological order (oldest first)."""
    with patch("monitor_server.read_all_events", return_value=[]):
        with patch("monitor_server.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 2, 15, 12, 0, 0, tzinfo=timezone.utc)
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = poll_success_rate()

    hours = [s["hour"] for s in result]
    assert hours == sorted(hours)
    assert hours[0].startswith("2026-02-14T13")
    assert hours[-1].startswith("2026-02-15T12")
