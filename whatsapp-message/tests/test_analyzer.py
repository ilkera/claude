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


def test_valid_response(config, posts):
    data = {
        "summary": ["Announced new tariffs", "Markets reacted"],
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
    assert len(result.summary) == 2
    assert "tariffs" in result.topics


def test_low_relevance(config, posts):
    data = {
        "summary": ["Minor post"],
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
