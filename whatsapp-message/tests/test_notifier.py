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
def analysis():
    return Analysis(
        summary=["Announced new 25% tariffs", "Claims trade deficit at historic levels"],
        topics=["economy", "tariffs"],
        relevance_score=0.85,
        original_posts=[
            Post(platform="truth_social", content="tariffs", timestamp="2026-01-01")
        ],
    )


def test_correct_params(config, analysis):
    with patch("notifier.Client") as mock_cls:
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.sid = "SM123"
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        notifier = WhatsAppNotifier(config)
        notifier.client = mock_client
        sid, body = notifier.send(analysis)

    assert sid == "SM123"
    assert isinstance(body, str)
    assert len(body) > 0
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["from_"] == config.twilio_whatsapp_from
    assert call_kwargs["to"] == config.whatsapp_to


def test_message_format(config, analysis):
    with patch("notifier.Client") as mock_cls:
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.sid = "SM123"
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        notifier = WhatsAppNotifier(config)
        notifier.client = mock_client
        notifier.send(analysis)

    body = mock_client.messages.create.call_args.kwargs["body"]
    assert "*Trump Post Alert*" in body
    assert "#economy" in body
    assert "#tariffs" in body
    assert "- Announced new 25% tariffs" in body
    assert "_Relevance: 85%_" in body


def test_message_length_constraint(config):
    long_analysis = Analysis(
        summary=["x" * 200] * 10,
        topics=["topic"] * 3,
        relevance_score=0.9,
    )
    with patch("notifier.Client") as mock_cls:
        mock_client = MagicMock()
        mock_msg = MagicMock()
        mock_msg.sid = "SM123"
        mock_client.messages.create.return_value = mock_msg
        mock_cls.return_value = mock_client

        notifier = WhatsAppNotifier(config)
        notifier.client = mock_client
        notifier.send(long_analysis)

    body = mock_client.messages.create.call_args.kwargs["body"]
    assert len(body) <= MAX_MESSAGE_LENGTH


def test_twilio_error(config, analysis):
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
            notifier.send(analysis)
