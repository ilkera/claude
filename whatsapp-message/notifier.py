from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from twilio.rest import Client

from config import Config
from models import Analysis

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 1600

SENTIMENT_EMOJI = {
    "bullish": "\U0001f7e2",   # green circle
    "bearish": "\U0001f534",   # red circle
    "neutral": "\u26aa",       # white circle
}


class WhatsAppNotifier:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = Client(config.twilio_account_sid, config.twilio_auth_token)

    def send(self, analysis: Analysis) -> tuple[str, str]:
        body = self._format_message(analysis)
        message = self.client.messages.create(
            from_=self.config.twilio_whatsapp_from,
            to=self.config.whatsapp_to,
            body=body,
        )
        logger.info("WhatsApp message sent: %s", message.sid)
        return message.sid, body

    def _format_message(self, analysis: Analysis) -> str:
        now = datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M ET")
        tags = " ".join(f"#{t}" for t in analysis.topics)
        relevance_pct = int(analysis.relevance_score * 100)

        # Classification header
        if analysis.primary_category is not None:
            if analysis.is_economic:
                sentiment_icon = SENTIMENT_EMOJI.get(analysis.market_sentiment or "", "\u26aa")
                if analysis.subcategory:
                    category_line = f"{sentiment_icon} [{analysis.primary_category} \u2192 {analysis.subcategory}]"
                else:
                    category_line = f"{sentiment_icon} [{analysis.primary_category}]"
            else:
                category_line = f"\U0001f4cc [{analysis.primary_category}]"

            confidence_pct = int((analysis.confidence or 0) * 100)
            msg = (
                f"*Trump Post Alert* ({now})\n"
                f"{category_line}\n"
                f"{tags}\n\n"
                f"{analysis.summary}\n\n"
                f"_Relevance: {relevance_pct}% | Confidence: {confidence_pct}%_"
            )
        else:
            # Fallback: no classification fields (backwards compat)
            msg = (
                f"*Trump Post Alert* ({now})\n"
                f"{tags}\n\n"
                f"{analysis.summary}\n\n"
                f"_Relevance: {relevance_pct}%_"
            )

        if len(msg) > MAX_MESSAGE_LENGTH:
            msg = msg[:MAX_MESSAGE_LENGTH - 3] + "..."
        return msg
