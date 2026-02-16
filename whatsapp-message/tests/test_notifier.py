from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from config import Config
from models import Analysis, Post
from notifier import WhatsAppNotifier, MAX_MESSAGE_LENGTH


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def economic_analysis():
    return Analysis(
        summary="Announced new 25% tariffs on Chinese electronics effective next month.",
        topics=["tariffs", "china", "economy"],
        relevance_score=0.85,
        original_posts=[
            Post(platform="truth_social", content="tariffs", timestamp="2026-01-01")
        ],
        is_economic=True,
        primary_category="Trade & Tariffs",
        subcategory="Tariff Announcements/Threats",
        secondary_category=None,
        market_sentiment="bearish",
        confidence=0.92,
    )


@pytest.fixture
def non_economic_analysis():
    return Analysis(
        summary="Praised border patrol for record deportation numbers this quarter.",
        topics=["immigration", "border"],
        relevance_score=0.7,
        original_posts=[
            Post(platform="truth_social", content="border", timestamp="2026-01-01")
        ],
        is_economic=False,
        primary_category="Immigration & Border",
        subcategory=None,
        secondary_category=None,
        market_sentiment=None,
        confidence=0.88,
    )


@pytest.fixture
def legacy_analysis():
    """Analysis without classification fields (backwards compat)."""
    return Analysis(
        summary="Some post summary.",
        topics=["economy", "tariffs"],
        relevance_score=0.85,
        original_posts=[
            Post(platform="truth_social", content="tariffs", timestamp="2026-01-01")
        ],
    )


def _make_notifier(config):
    with patch("notifier.Client") as mock_cls:
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.sid = "SM123"
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client
        notifier = WhatsAppNotifier(config)
        notifier.client = mock_client
        return notifier, mock_client


def test_economic_message_format(config, economic_analysis):
    notifier, mock_client = _make_notifier(config)
    sid, body = notifier.send(economic_analysis)

    assert sid == "SM123"
    assert "*Trump Post Alert*" in body
    assert "[Trade & Tariffs \u2192 Tariff Announcements/Threats]" in body
    assert "\U0001f534" in body  # red circle for bearish
    assert "#tariffs" in body
    assert "Announced new 25% tariffs" in body
    assert "Relevance: 85%" in body
    assert "Confidence: 92%" in body


def test_non_economic_message_format(config, non_economic_analysis):
    notifier, mock_client = _make_notifier(config)
    sid, body = notifier.send(non_economic_analysis)

    assert "\U0001f4cc" in body  # pin emoji
    assert "[Immigration & Border]" in body
    assert "Praised border patrol" in body
    assert "Confidence: 88%" in body


def test_legacy_format_no_classification(config, legacy_analysis):
    notifier, mock_client = _make_notifier(config)
    sid, body = notifier.send(legacy_analysis)

    assert "*Trump Post Alert*" in body
    assert "#economy" in body
    assert "Relevance: 85%" in body
    # No classification header
    assert "\U0001f4cc" not in body
    assert "\u2192" not in body
    # No confidence in legacy format
    assert "Confidence" not in body


def test_correct_params(config, economic_analysis):
    notifier, mock_client = _make_notifier(config)
    notifier.send(economic_analysis)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["from_"] == config.twilio_whatsapp_from
    assert call_kwargs["to"] == config.whatsapp_to


def test_message_length_constraint(config):
    long_analysis = Analysis(
        summary="x" * 2000,
        topics=["topic"] * 3,
        relevance_score=0.9,
        is_economic=True,
        primary_category="Trade & Tariffs",
        subcategory="Tariff Announcements/Threats",
        market_sentiment="bearish",
        confidence=0.9,
    )
    notifier, mock_client = _make_notifier(config)
    notifier.send(long_analysis)

    body = mock_client.messages.create.call_args.kwargs["body"]
    assert len(body) <= MAX_MESSAGE_LENGTH


def test_twilio_error(config, economic_analysis):
    from twilio.base.exceptions import TwilioRestException

    with patch("notifier.Client") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = TwilioRestException(
            status=400, uri="/messages", msg="Bad request"
        )
        mock_cls.return_value = mock_client

        notifier = WhatsAppNotifier(config)
        notifier.client = mock_client

        with pytest.raises(TwilioRestException):
            notifier.send(economic_analysis)


def test_bullish_sentiment_emoji(config):
    analysis = Analysis(
        summary="Market rally expected.",
        topics=["stocks"],
        relevance_score=0.8,
        is_economic=True,
        primary_category="Stock Market & Equities",
        subcategory="General Market Commentary",
        market_sentiment="bullish",
        confidence=0.85,
    )
    notifier, _ = _make_notifier(config)
    _, body = notifier.send(analysis)
    assert "\U0001f7e2" in body  # green circle for bullish


def test_neutral_sentiment_emoji(config):
    analysis = Analysis(
        summary="Fed commentary with no clear direction.",
        topics=["fed"],
        relevance_score=0.6,
        is_economic=True,
        primary_category="Monetary Policy & The Fed",
        subcategory="Interest Rate Commentary",
        market_sentiment="neutral",
        confidence=0.75,
    )
    notifier, _ = _make_notifier(config)
    _, body = notifier.send(analysis)
    assert "\u26aa" in body  # white circle for neutral
