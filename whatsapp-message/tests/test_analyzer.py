from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from analyzer import PostAnalyzer
from config import Config
from models import Post


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def posts():
    return [
        Post(
            platform="truth_social",
            content="New tariffs announced today",
            timestamp="2026-01-01T12:00:00",
        )
    ]


def _mock_response(text: str) -> MagicMock:
    content_block = MagicMock()
    content_block.text = text
    resp = MagicMock()
    resp.content = [content_block]
    return resp


def test_valid_economic_response(config, posts):
    data = {
        "is_economic": True,
        "primary_category": "Trade & Tariffs",
        "subcategory": "Tariff Announcements/Threats",
        "secondary_category": None,
        "market_sentiment": "bearish",
        "confidence": 0.92,
        "summary": "Announced new 25% tariffs on Chinese electronics.",
        "topics": ["tariffs", "economy"],
        "relevance_score": 0.8,
    }
    with patch("analyzer.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(json.dumps(data))
        mock_cls.return_value = mock_client

        analyzer = PostAnalyzer(config)
        analyzer.client = mock_client
        result = analyzer.analyze(posts)

    assert result is not None
    assert result.relevance_score == 0.8
    assert result.is_economic is True
    assert result.primary_category == "Trade & Tariffs"
    assert result.subcategory == "Tariff Announcements/Threats"
    assert result.market_sentiment == "bearish"
    assert result.confidence == 0.92
    assert isinstance(result.summary, str)
    assert "tariffs" in result.topics


def test_valid_non_economic_response(config, posts):
    data = {
        "is_economic": False,
        "primary_category": "Immigration & Border",
        "subcategory": None,
        "secondary_category": None,
        "market_sentiment": None,
        "confidence": 0.88,
        "summary": "Praised border patrol for record deportation numbers.",
        "topics": ["immigration"],
        "relevance_score": 0.7,
    }
    with patch("analyzer.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(json.dumps(data))
        mock_cls.return_value = mock_client

        analyzer = PostAnalyzer(config)
        analyzer.client = mock_client
        result = analyzer.analyze(posts)

    assert result is not None
    assert result.is_economic is False
    assert result.primary_category == "Immigration & Border"
    assert result.subcategory is None
    assert result.market_sentiment is None


def test_low_relevance(config, posts):
    data = {
        "is_economic": False,
        "primary_category": "Personal & Self-Promotion",
        "subcategory": None,
        "secondary_category": None,
        "market_sentiment": None,
        "confidence": 0.9,
        "summary": "Minor personal post.",
        "topics": ["misc"],
        "relevance_score": 0.1,
    }
    with patch("analyzer.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(json.dumps(data))
        mock_cls.return_value = mock_client

        analyzer = PostAnalyzer(config)
        analyzer.client = mock_client
        result = analyzer.analyze(posts)

    assert result is None


def test_empty_posts(config):
    analyzer = PostAnalyzer(config)
    assert analyzer.analyze([]) is None


def test_malformed_json(config, posts):
    with patch("analyzer.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response("not json at all")
        mock_cls.return_value = mock_client

        analyzer = PostAnalyzer(config)
        analyzer.client = mock_client
        result = analyzer.analyze(posts)

    assert result is None


def test_api_error(config, posts):
    import anthropic as anthropic_mod

    with patch("analyzer.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic_mod.APIError(
            message="rate limited",
            request=MagicMock(),
            body=None,
        )
        mock_cls.return_value = mock_client

        analyzer = PostAnalyzer(config)
        analyzer.client = mock_client
        result = analyzer.analyze(posts)

    assert result is None


def test_system_prompt_includes_taxonomy(config, posts):
    """The system prompt should include the taxonomy text."""
    data = {
        "is_economic": True,
        "primary_category": "Tax Policy",
        "subcategory": "Corporate Tax",
        "secondary_category": None,
        "market_sentiment": "bullish",
        "confidence": 0.85,
        "summary": "Proposed cutting corporate tax rate.",
        "topics": ["taxes"],
        "relevance_score": 0.8,
    }
    with patch("analyzer.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(json.dumps(data))
        mock_cls.return_value = mock_client

        analyzer = PostAnalyzer(config)
        analyzer.client = mock_client
        analyzer.analyze(posts)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    system = call_kwargs["system"]
    assert "Trade & Tariffs" in system
    assert "Immigration & Border" in system
