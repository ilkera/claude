from __future__ import annotations

import json
import logging

from playwright.async_api import async_playwright, Browser, Playwright

from config import Config

logger = logging.getLogger(__name__)

API_PATH = "/wp-json/factbase/v1/twitter?sort=date&sort_order=desc&format=json&page=1"


class Scraper:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        logger.info("Browser launched")

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")

    async def fetch_posts(self) -> list[dict]:
        """Fetch posts from the JSON API, returns list of post dicts."""
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")

        # Build API URL from the base scrape URL's origin
        from urllib.parse import urlparse

        parsed = urlparse(self.config.scrape_url)
        api_url = f"{parsed.scheme}://{parsed.netloc}{API_PATH}"

        page = await self._browser.new_page()
        try:
            logger.info("Fetching API: %s", api_url)
            response = await page.goto(
                api_url,
                timeout=self.config.page_load_timeout_ms,
                wait_until="networkidle",
            )
            text = await page.evaluate("() => document.body.innerText")
            data = json.loads(text)

            posts = data.get("data", [])
            logger.info("API returned %d posts", len(posts))
            return posts
        finally:
            await page.close()
