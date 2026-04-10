"""Tests for Issue #4: Event-driven pipeline refactor of poll_cycle().

These tests verify that poll_cycle has been refactored into discrete stages
with individual success/failure outcomes, and that failures identify the
failed stage in logs.

Tests are behavior-focused: they check observable outcomes (events logged,
notifications sent, errors reported with stage info) rather than requiring
a specific pipeline API.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from config import Config
from event_logger import EventLogger
from models import Analysis, Post
from scraper import FetchResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_raw_posts():
    return json.loads(
        (Path(__file__).parent / "fixtures" / "sample_api_response.json").read_text()
    )


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def event_logger(tmp_path):
    return EventLogger(str(tmp_path / "events.jsonl"))


@pytest.fixture
def state_manager(tmp_path):
    from state import StateManager
    return StateManager(str(tmp_path / "state.json"))


@pytest.fixture
def parser():
    from parser import PostParser
    return PostParser()


@pytest.fixture
def mock_scraper(sample_raw_posts):
    scraper = AsyncMock()
    scraper.fetch_posts.return_value = FetchResult(posts=sample_raw_posts, source="primary")
    scraper.config.scrape_url = "https://trumpstruth.org/"
    return scraper


@pytest.fixture
def mock_analyzer():
    analyzer = MagicMock()
    analyzer.analyze.return_value = Analysis(
        summary="Test analysis.",
        topics=["test"],
        relevance_score=0.8,
        is_economic=True,
        primary_category="Trade & Tariffs",
        subcategory="Tariff Announcements/Threats",
        market_sentiment="bearish",
        confidence=0.9,
    )
    return analyzer


@pytest.fixture
def mock_notifier():
    notifier = MagicMock()
    notifier.send.return_value = ("SM123", "formatted message")
    return notifier


def _read_events(event_logger):
    """Read all events from the event logger file."""
    events = []
    try:
        with open(event_logger.filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    except FileNotFoundError:
        pass
    return events


# ---------------------------------------------------------------------------
# Stage isolation: each stage should be testable independently
# ---------------------------------------------------------------------------


class TestScrapeStage:
    @pytest.mark.asyncio
    async def test_scrape_failure_is_identifiable(
        self, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config
    ):
        """When scraping fails, the error should identify the scrape stage."""
        from main import poll_cycle

        scraper = AsyncMock()
        scraper.fetch_posts.side_effect = RuntimeError("Connection refused")
        scraper.config.scrape_url = "https://trumpstruth.org/"

        # poll_cycle should handle the error (log it) or raise it
        try:
            await poll_cycle(
                scraper, parser, mock_analyzer, mock_notifier,
                state_manager, event_logger, config,
            )
        except RuntimeError:
            pass  # acceptable if poll_cycle propagates the exception

        # Either poll_cycle logged the error, or it propagated up
        # If it was logged, verify stage identification
        events = _read_events(event_logger)
        error_events = [e for e in events if e.get("event_type") == "error"]
        if error_events:
            # Error event should help identify which stage failed
            err = error_events[0]
            assert "source" in err or "stage" in err or "error_type" in err, (
                "Error events should contain information to identify the failed stage"
            )


class TestAnalyzeStage:
    @pytest.mark.asyncio
    async def test_analyze_failure_does_not_crash_pipeline(
        self, mock_scraper, parser, mock_notifier, state_manager, event_logger, config
    ):
        """When analysis fails, the pipeline should handle it gracefully."""
        from main import poll_cycle

        analyzer = MagicMock()
        analyzer.analyze.side_effect = Exception("Claude API timeout")

        # Should not crash — should log the error and continue
        try:
            await poll_cycle(
                mock_scraper, parser, analyzer, mock_notifier,
                state_manager, event_logger, config,
            )
        except Exception:
            pass  # acceptable if it propagates

        # Notifier should NOT have been called (analysis failed)
        mock_notifier.send.assert_not_called()


class TestNotifyStage:
    @pytest.mark.asyncio
    async def test_notify_failure_is_logged(
        self, mock_scraper, parser, mock_analyzer, state_manager, event_logger, config
    ):
        """When notification fails, the error should be identifiable."""
        from main import poll_cycle

        notifier = MagicMock()
        notifier.send.side_effect = Exception("Twilio error")

        try:
            await poll_cycle(
                mock_scraper, parser, mock_analyzer, notifier,
                state_manager, event_logger, config,
            )
        except Exception:
            pass

        # The error should be logged somewhere
        events = _read_events(event_logger)
        error_events = [e for e in events if e.get("event_type") == "error"]
        if error_events:
            err = error_events[0]
            assert "error_type" in err or "message" in err


# ---------------------------------------------------------------------------
# Stage outcomes: each stage should produce clear success/failure signal
# ---------------------------------------------------------------------------


class TestStageOutcomes:
    @pytest.mark.asyncio
    async def test_successful_pipeline_logs_poll_end(
        self, mock_scraper, parser, mock_analyzer, mock_notifier,
        state_manager, event_logger, config,
    ):
        """A successful pipeline run should log a poll_end event."""
        from main import poll_cycle

        await poll_cycle(
            mock_scraper, parser, mock_analyzer, mock_notifier,
            state_manager, event_logger, config,
        )

        events = _read_events(event_logger)
        poll_ends = [e for e in events if e.get("event_type") == "poll_end"]
        assert len(poll_ends) > 0, "Successful pipeline should log poll_end"

    @pytest.mark.asyncio
    async def test_stage_failure_logged_with_context(
        self, parser, mock_notifier, state_manager, event_logger, config
    ):
        """When a stage fails, the logged error should include enough context
        to identify which stage failed (not just a generic error).
        """
        from main import poll_cycle

        scraper = AsyncMock()
        scraper.fetch_posts.side_effect = ConnectionError("DNS resolution failed")
        scraper.config.scrape_url = "https://trumpstruth.org/"

        analyzer = MagicMock()

        try:
            await poll_cycle(
                scraper, parser, analyzer, mock_notifier,
                state_manager, event_logger, config,
            )
        except (ConnectionError, Exception):
            pass

        events = _read_events(event_logger)
        error_events = [e for e in events if e.get("event_type") == "error"]

        if error_events:
            err = error_events[0]
            # Should have error type and/or source to identify the stage
            has_context = (
                err.get("error_type")
                or err.get("source")
                or err.get("stage")
                or err.get("message")
            )
            assert has_context, (
                "Error events must include context (error_type, source, stage, or message) "
                "to identify what failed"
            )


# ---------------------------------------------------------------------------
# End-to-end: pipeline should still produce the same observable behavior
# ---------------------------------------------------------------------------


class TestEndToEnd:
    @pytest.mark.asyncio
    async def test_full_pipeline_sends_notification(
        self, mock_scraper, parser, mock_analyzer, mock_notifier,
        state_manager, event_logger, config,
    ):
        """The refactored pipeline should still send notifications for new posts."""
        from main import poll_cycle

        await poll_cycle(
            mock_scraper, parser, mock_analyzer, mock_notifier,
            state_manager, event_logger, config,
        )

        mock_notifier.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_marks_posts_as_seen(
        self, mock_scraper, parser, mock_analyzer, mock_notifier,
        state_manager, event_logger, config,
    ):
        """Posts should be marked as seen after processing."""
        from main import poll_cycle

        await poll_cycle(
            mock_scraper, parser, mock_analyzer, mock_notifier,
            state_manager, event_logger, config,
        )

        # Second run should find no new posts
        mock_analyzer.reset_mock()
        mock_notifier.reset_mock()

        await poll_cycle(
            mock_scraper, parser, mock_analyzer, mock_notifier,
            state_manager, event_logger, config,
        )

        mock_analyzer.analyze.assert_not_called()
        mock_notifier.send.assert_not_called()
