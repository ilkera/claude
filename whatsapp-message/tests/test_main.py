from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from config import Config
from main import poll_cycle
from models import Analysis
from scraper import FetchResult


@pytest.fixture
def sample_raw_posts():
    return json.loads(
        (Path(__file__).parent / "fixtures" / "sample_api_response.json").read_text()
    )


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
        summary="Tariff announcement on Chinese goods.",
        topics=["tariffs"],
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
    notifier.send.return_value = ("SM123", "formatted message body")
    return notifier


@pytest.fixture
def state_manager(tmp_path):
    from state import StateManager
    return StateManager(str(tmp_path / "state.json"))


@pytest.fixture
def parser():
    from parser import PostParser
    return PostParser()


@pytest.fixture
def event_logger(tmp_path):
    from event_logger import EventLogger
    return EventLogger(str(tmp_path / "events.jsonl"))


@pytest.fixture
def config():
    return Config()


@pytest.mark.asyncio
async def test_full_cycle_with_new_posts(
    mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config
):
    await poll_cycle(mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config)

    mock_scraper.fetch_posts.assert_called_once()
    mock_analyzer.analyze.assert_called_once()
    mock_notifier.send.assert_called_once()


@pytest.mark.asyncio
async def test_no_new_posts(
    mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config
):
    # First cycle sees all posts
    await poll_cycle(mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config)

    mock_analyzer.reset_mock()
    mock_notifier.reset_mock()

    # Second cycle - no new posts
    await poll_cycle(mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config)

    mock_analyzer.analyze.assert_not_called()
    mock_notifier.send.assert_not_called()


@pytest.mark.asyncio
async def test_scraper_failure(parser, mock_analyzer, mock_notifier, state_manager, event_logger, config):
    scraper = AsyncMock()
    scraper.fetch_posts.side_effect = RuntimeError("Browser crashed")
    scraper.config.scrape_url = "https://trumpstruth.org/"

    with pytest.raises(RuntimeError):
        await poll_cycle(scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config)


@pytest.mark.asyncio
async def test_analysis_below_threshold(
    mock_scraper, parser, mock_notifier, state_manager, event_logger, config
):
    analyzer = MagicMock()
    analyzer.analyze.return_value = None  # Below threshold

    await poll_cycle(mock_scraper, parser, analyzer, mock_notifier, state_manager, event_logger, config)

    mock_notifier.send.assert_not_called()


@pytest.mark.asyncio
async def test_source_propagated_to_events(
    sample_raw_posts, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config
):
    """The source field from FetchResult is included in poll_end events."""
    scraper = AsyncMock()
    scraper.fetch_posts.return_value = FetchResult(posts=sample_raw_posts, source="fallback")
    scraper.config.scrape_url = "https://trumpstruth.org/"

    await poll_cycle(scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config)

    # Read back events and check poll_end has source=fallback
    events = []
    with open(event_logger.filepath) as f:
        for line in f:
            events.append(json.loads(line.strip()))
    poll_ends = [e for e in events if e["event_type"] == "poll_end"]
    assert len(poll_ends) == 1
    assert poll_ends[0]["source"] == "fallback"


@pytest.mark.asyncio
async def test_non_economic_filtering(
    mock_scraper, parser, mock_notifier, state_manager, event_logger
):
    """Non-economic posts are filtered when notify_non_economic is False."""
    config = Config()
    config.notify_non_economic = False

    analyzer = MagicMock()
    analyzer.analyze.return_value = Analysis(
        summary="Praised border patrol numbers.",
        topics=["immigration"],
        relevance_score=0.7,
        is_economic=False,
        primary_category="Immigration & Border",
        subcategory=None,
        market_sentiment=None,
        confidence=0.88,
    )

    await poll_cycle(mock_scraper, parser, analyzer, mock_notifier, state_manager, event_logger, config)

    mock_notifier.send.assert_not_called()

    # Verify the skip was logged
    events = []
    with open(event_logger.filepath) as f:
        for line in f:
            events.append(json.loads(line.strip()))
    skipped = [e for e in events if e["event_type"] == "notification_skipped"]
    assert any(e.get("reason") == "non_economic_filtered" for e in skipped)


@pytest.mark.asyncio
async def test_notification_event_has_classification_fields(
    mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config
):
    """notification_sent events include classification fields."""
    await poll_cycle(mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger, config)

    events = []
    with open(event_logger.filepath) as f:
        for line in f:
            events.append(json.loads(line.strip()))
    sent = [e for e in events if e["event_type"] == "notification_sent"]
    assert len(sent) == 1
    assert sent[0]["is_economic"] is True
    assert sent[0]["primary_category"] == "Trade & Tariffs"
    assert sent[0]["subcategory"] == "Tariff Announcements/Threats"
    assert sent[0]["market_sentiment"] == "bearish"
    assert sent[0]["confidence"] == 0.9
