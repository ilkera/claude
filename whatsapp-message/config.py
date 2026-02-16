from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Twilio
    twilio_account_sid: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_whatsapp_from: str = os.getenv("TWILIO_WHATSAPP_FROM", "")
    whatsapp_to: str = os.getenv("WHATSAPP_TO", "")

    # Anthropic
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    claude_model: str = os.getenv("CLAUDE_MODEL", "claude-opus-4-6")

    # Scraping
    scrape_url: str = os.getenv(
        "SCRAPE_URL",
        "https://trumpstruth.org/",
    )
    fallback_scrape_url: str = os.getenv(
        "FALLBACK_SCRAPE_URL",
        "https://rollcall.com/factbase/trump/topic/social",
    )
    poll_interval_seconds: int = int(os.getenv("POLL_INTERVAL_SECONDS", "420"))
    page_load_timeout_ms: int = int(os.getenv("PAGE_LOAD_TIMEOUT_MS", "60000"))

    # State
    state_file: str = os.getenv("STATE_FILE", "seen_posts.json")

    # Filter
    min_relevance_score: float = float(os.getenv("MIN_RELEVANCE_SCORE", "0.3"))

    # Monitoring
    events_file: str = os.getenv("EVENTS_FILE", "events_log.json")
    monitor_port: int = int(os.getenv("MONITOR_PORT", "8080"))
