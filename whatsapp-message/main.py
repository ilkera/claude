from __future__ import annotations

import asyncio
import logging
import sys

from analyzer import PostAnalyzer
from config import Config
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
) -> None:
    logger.info("Starting poll cycle")

    raw_posts = await scraper.fetch_posts()
    posts = parser.parse(raw_posts)

    new_posts = state.filter_new(posts)
    if not new_posts:
        logger.info("No new posts found")
        return

    logger.info("Found %d new posts", len(new_posts))
    analysis = analyzer.analyze(new_posts)
    state.mark_seen(new_posts)

    if analysis:
        sid = notifier.send(analysis)
        logger.info("Notification sent: %s", sid)
    else:
        logger.info("Analysis below threshold or failed, skipping notification")


async def main() -> None:
    config = Config()
    scraper = Scraper(config)
    parser = PostParser()
    analyzer = PostAnalyzer(config)
    notifier = WhatsAppNotifier(config)
    state = StateManager(config.state_file)

    await scraper.start()
    try:
        while True:
            try:
                await poll_cycle(scraper, parser, analyzer, notifier, state)
            except Exception:
                logger.exception("Poll cycle failed")
            logger.info("Sleeping %d seconds", config.poll_interval_seconds)
            await asyncio.sleep(config.poll_interval_seconds)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        await scraper.stop()


if __name__ == "__main__":
    asyncio.run(main())
