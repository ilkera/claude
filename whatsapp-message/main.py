from __future__ import annotations

import asyncio
import logging
import os
import sys
import time

from analyzer import PostAnalyzer
from config import Config
from event_logger import EventLogger
from notifier import WhatsAppNotifier
from parser import PostParser
from scraper import Scraper
from state import StateManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("monitor.log"),
    ],
)
logger = logging.getLogger(__name__)


async def poll_cycle(
    scraper: Scraper,
    parser: PostParser,
    analyzer: PostAnalyzer,
    notifier: WhatsAppNotifier,
    state: StateManager,
    event_logger: EventLogger,
) -> None:
    logger.info("Starting poll cycle")
    event_logger.log("poll_start", url=scraper.config.scrape_url)
    t0 = time.monotonic()

    result = await scraper.fetch_posts()
    raw_posts, source = result.posts, result.source
    posts = parser.parse(raw_posts)

    new_posts = state.filter_new(posts)
    if not new_posts:
        logger.info("No new posts found")
        duration_ms = int((time.monotonic() - t0) * 1000)
        event_logger.log(
            "poll_end", posts_found=len(posts), new_posts=0, new_post_ids=[], duration_ms=duration_ms, source=source
        )
        event_logger.log("notification_skipped", reason="no_new_posts")
        return

    logger.info("Found %d new posts", len(new_posts))
    analysis = analyzer.analyze(new_posts)
    state.mark_seen(new_posts)

    if analysis:
        sid = notifier.send(analysis)
        logger.info("Notification sent: %s", sid)
        event_logger.log(
            "notification_sent",
            sid=sid,
            topics=analysis.topics,
            relevance_score=analysis.relevance_score,
            summary=analysis.summary,
        )
    else:
        logger.info("Analysis below threshold or failed, skipping notification")
        event_logger.log("notification_skipped", reason="below_threshold")

    duration_ms = int((time.monotonic() - t0) * 1000)
    event_logger.log(
        "poll_end",
        posts_found=len(posts),
        new_posts=len(new_posts),
        new_post_ids=[p.post_id for p in new_posts],
        duration_ms=duration_ms,
        source=source,
    )


async def main() -> None:
    config = Config()
    scraper = Scraper(config)
    parser = PostParser()
    analyzer = PostAnalyzer(config)
    notifier = WhatsAppNotifier(config)
    state = StateManager(config.state_file)
    event_logger = EventLogger(config.events_file)

    pid_file = config.events_file.replace(".json", ".pid")
    if os.path.exists(pid_file):
        try:
            old_pid = int(open(pid_file).read().strip())
            os.kill(old_pid, 0)
            logger.error("Another instance is already running (PID %d). Exiting.", old_pid)
            sys.exit(1)
        except (OSError, ValueError):
            pass  # process not running or invalid pid, safe to continue
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    event_logger.log("service_start")
    await scraper.start()
    try:
        while True:
            try:
                await poll_cycle(
                    scraper, parser, analyzer, notifier, state, event_logger
                )
            except Exception:
                logger.exception("Poll cycle failed")
                event_logger.log(
                    "error",
                    error_type=sys.exc_info()[0].__name__ if sys.exc_info()[0] else "Unknown",
                    message=str(sys.exc_info()[1]),
                    source="unknown",
                )
            logger.info("Sleeping %d seconds", config.poll_interval_seconds)
            await asyncio.sleep(config.poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        event_logger.log("service_stop", reason="shutdown")
        if os.path.exists(pid_file):
            os.unlink(pid_file)
        await scraper.stop()


if __name__ == "__main__":
    asyncio.run(main())
