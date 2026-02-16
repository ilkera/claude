from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import NamedTuple
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, Playwright

from config import Config

logger = logging.getLogger(__name__)

API_PATH = "/wp-json/factbase/v1/twitter?sort=date&sort_order=desc&format=json&page=1"


class FetchResult(NamedTuple):
    posts: list[dict]
    source: str  # "primary" or "fallback"


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

    async def _ensure_browser(self) -> None:
        """Relaunch the browser if the connection was lost."""
        if self._browser and self._browser.is_connected():
            return
        logger.warning("Browser connection lost, relaunching")
        try:
            if self._browser:
                await self._browser.close()
        except Exception:
            pass
        if not self._playwright:
            self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        logger.info("Browser relaunched")

    async def fetch_posts(self) -> FetchResult:
        """Fetch posts from primary source, falling back to secondary on failure."""
        if not self._browser and not self._playwright:
            raise RuntimeError("Browser not started. Call start() first.")
        await self._ensure_browser()

        primary_url = self.config.scrape_url
        fallback_url = self.config.fallback_scrape_url

        # Try primary
        try:
            posts = await self._fetch(primary_url)
            logger.info("Primary source returned %d posts", len(posts))
            return FetchResult(posts=posts, source="primary")
        except Exception as exc:
            logger.warning("Primary source failed (%s): %s", type(exc).__name__, exc)
            if not fallback_url:
                raise

        # Try fallback
        posts = await self._fetch(fallback_url)
        logger.info("Fallback source returned %d posts", len(posts))
        return FetchResult(posts=posts, source="fallback")

    async def _fetch(self, url: str) -> list[dict]:
        """Route to the appropriate fetcher based on URL."""
        parsed = urlparse(url)
        if "trumpstruth.org" in parsed.netloc:
            return await self._fetch_from_html(url)
        return await self._fetch_from_api(url)

    async def _fetch_from_html(self, url: str) -> list[dict]:
        """Fetch posts from trumpstruth.org by parsing server-rendered HTML."""
        page = await self._browser.new_page()
        try:
            logger.info("Fetching HTML: %s", url)
            await page.goto(
                url,
                timeout=self.config.page_load_timeout_ms,
                wait_until="domcontentloaded",
            )
            # Wait for dynamic content
            await page.wait_for_timeout(5000)

            statuses = await page.query_selector_all(".status")
            posts: list[dict] = []
            for status in statuses:
                try:
                    post = await self._parse_status_element(status, url)
                    if post:
                        posts.append(post)
                except Exception as exc:
                    logger.debug("Failed to parse a status element: %s", exc)
                    continue

            logger.info("HTML parser extracted %d posts", len(posts))
            return posts
        finally:
            await page.close()

    async def _parse_status_element(self, status, base_url: str) -> dict | None:
        """Extract a single post dict from a .status element."""
        # Text content
        content_el = await status.query_selector(".status__content")
        text = await content_el.inner_text() if content_el else ""
        text = text.strip()
        if not text:
            return None

        # Timestamp
        meta_el = await status.query_selector(".status-info__meta")
        date_str = ""
        if meta_el:
            raw_date = (await meta_el.inner_text()).strip()
            date_str = self._parse_human_date(raw_date)

        # Link / document ID
        link_el = await status.query_selector(".status-header__right a")
        post_url = ""
        document_id = ""
        if link_el:
            href = await link_el.get_attribute("href") or ""
            if href:
                parsed = urlparse(base_url)
                post_url = f"{parsed.scheme}://{parsed.netloc}{href}"
                # Extract ID from path like /statuses/36709
                match = re.search(r"/statuses/(\d+)", href)
                document_id = match.group(1) if match else ""

        # Generate a stable document_id if none found
        if not document_id:
            document_id = hashlib.sha256(f"{text}{date_str}".encode()).hexdigest()[:16]

        # Image
        img_el = await status.query_selector(".status__attachments img")
        image_url = ""
        if img_el:
            image_url = await img_el.get_attribute("src") or ""

        return {
            "text": text,
            "date": date_str,
            "document_id": document_id,
            "image_url": image_url,
            "url": post_url,
        }

    @staticmethod
    def _parse_human_date(raw: str) -> str:
        """Parse human-readable date like 'February 14, 2026, 10:05 AM' to ISO format."""
        # Try common formats
        for fmt in (
            "%B %d, %Y, %I:%M %p",
            "%B %d, %Y, %I:%M:%S %p",
            "%B %d, %Y",
        ):
            try:
                dt = datetime.strptime(raw, fmt)
                return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
            except ValueError:
                continue
        logger.debug("Could not parse date: %s", raw)
        return raw

    async def _fetch_from_api(self, base_url: str) -> list[dict]:
        """Fetch posts from the Factbase JSON API (rollcall.com)."""
        parsed = urlparse(base_url)
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
