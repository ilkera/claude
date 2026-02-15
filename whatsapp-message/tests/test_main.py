from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from main import poll_cycle
from models import Analysis


@pytest.fixture
def sample_raw_posts():
    return json.loads(
        (Path(__file__).parent / "fixtures" / "sample_api_response.json").read_text()
    )


@pytest.fixture
def mock_scraper(sample_raw_posts):
    scraper = AsyncMock()
    scraper.fetch_posts.return_value = sample_raw_posts
    return scraper


@pytest.fixture
def mock_analyzer():
    analyzer = MagicMock()
    analyzer.analyze.return_value = Analysis(
        summary=["Tariff announcement", "Economy update"],
        topics=["tariffs"],
        relevance_score=0.8,
    )
    return analyzer


@pytest.fixture
def mock_notifier():
    notifier = MagicMock()
    notifier.send.return_value = "SM123"
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


@pytest.mark.asyncio
async def test_full_cycle_with_new_posts(
    mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger
):
    await poll_cycle(mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger)

    mock_scraper.fetch_posts.assert_called_once()
    mock_analyzer.analyze.assert_called_once()
    mock_notifier.send.assert_called_once()


@pytest.mark.asyncio
async def test_no_new_posts(
    mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger
):
    # First cycle sees all posts
    await poll_cycle(mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger)

    mock_analyzer.reset_mock()
    mock_notifier.reset_mock()

    # Second cycle - no new posts
    await poll_cycle(mock_scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger)

    mock_analyzer.analyze.assert_not_called()
    mock_notifier.send.assert_not_called()


@pytest.mark.asyncio
async def test_scraper_failure(parser, mock_analyzer, mock_notifier, state_manager, event_logger):
    scraper = AsyncMock()
    scraper.fetch_posts.side_effect = RuntimeError("Browser crashed")

    with pytest.raises(RuntimeError):
        await poll_cycle(scraper, parser, mock_analyzer, mock_notifier, state_manager, event_logger)


@pytest.mark.asyncio
async def test_analysis_below_threshold(
    mock_scraper, parser, mock_notifier, state_manager, event_logger
):
    analyzer = MagicMock()
    analyzer.analyze.return_value = None  # Below threshold

    await poll_cycle(mock_scraper, parser, analyzer, mock_notifier, state_manager, event_logger)

    mock_notifier.send.assert_not_called()
