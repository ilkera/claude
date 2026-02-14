from __future__ import annotations

import logging
from datetime import datetime, timezone

from twilio.rest import Client

from config import Config
from models import Analysis

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 1600


class WhatsAppNotifier:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = Client(config.twilio_account_sid, config.twilio_auth_token)

    def send(self, analysis: Analysis) -> str:
        body = self._format_message(analysis)
        message = self.client.messages.create(
            from_=self.config.twilio_whatsapp_from,
            to=self.config.whatsapp_to,
            body=body,
        )
        logger.info("WhatsApp message sent: %s", message.sid)
        return message.sid

    def _format_message(self, analysis: Analysis) -> str:
        now = datetime.now(timezone.utc).strftime("%H:%M UTC")
        tags = " ".join(f"#{t}" for t in analysis.topics)
        bullets = "\n".join(f"- {s}" for s in analysis.summary)
        relevance_pct = int(analysis.relevance_score * 100)

        msg = f"*Trump Post Alert* ({now})\n{tags}\n\n{bullets}\n\n_Relevance: {relevance_pct}%_"

        if len(msg) > MAX_MESSAGE_LENGTH:
            msg = msg[:MAX_MESSAGE_LENGTH - 3] + "..."
        return msg
