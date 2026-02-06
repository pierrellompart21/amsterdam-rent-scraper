"""Base scraper class for JavaScript-heavy sites using Playwright."""

import abc
import hashlib
import random
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, Browser
from rich.console import Console

from amsterdam_rent_scraper.config.settings import (
    RAW_PAGES_DIR,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
)

console = Console()


class PlaywrightBaseScraper(abc.ABC):
    """Abstract base for scrapers that need JavaScript rendering."""

    site_name: str = "unknown"

    def __init__(
        self, min_price: int = 1000, max_price: int = 2000, test_mode: bool = False
    ):
        self.min_price = min_price
        self.max_price = max_price
        self.test_mode = test_mode
        self.max_listings = 3 if test_mode else 10000
        RAW_PAGES_DIR.mkdir(parents=True, exist_ok=True)
        self._browser: Browser | None = None
        self._playwright = None

    @abc.abstractmethod
    def get_listing_urls(self, page: Page) -> list[str]:
        """Return list of individual listing URLs to scrape. Gets a Playwright page object."""
        ...

    @abc.abstractmethod
    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a listing page and return raw extracted data."""
        ...

    def _delay(self):
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    def _get_browser(self) -> Browser:
        """Get or create a browser instance."""
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
        return self._browser

    def _close_browser(self):
        """Close browser and cleanup."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def _new_page(self) -> Page:
        """Create a new page with common settings."""
        browser = self._get_browser()
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="nl-NL",
        )
        page = context.new_page()
        # Block unnecessary resources to speed up
        page.route(
            "**/*.{png,jpg,jpeg,gif,svg,webp,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )
        return page

    def fetch_page(self, url: str, page: Page | None = None, wait_selector: str | None = None) -> str:
        """Fetch a page with JavaScript rendering."""
        close_page = page is None
        if page is None:
            page = self._new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=60000)

            # Wait for specific selector if provided
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=10000)
                except Exception:
                    pass  # Continue even if selector not found

            # Small delay for dynamic content
            page.wait_for_timeout(1000)

            return page.content()
        finally:
            if close_page:
                page.close()

    def save_raw_page(self, url: str, html: str) -> str:
        """Save raw HTML to disk, return the file path."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"{self.site_name}_{url_hash}.html"
        path = RAW_PAGES_DIR / filename
        path.write_text(html, encoding="utf-8")
        return str(path)

    def scrape_all(self) -> list[dict]:
        """Full scrape pipeline: get URLs → fetch each → parse → return raw dicts."""
        console.print(f"[bold cyan]Scraping {self.site_name} (Playwright)...[/]")

        try:
            page = self._new_page()
            urls = self.get_listing_urls(page)
            page.close()

            if self.test_mode:
                urls = urls[: self.max_listings]
            console.print(f"  Found {len(urls)} listing URLs (limit: {self.max_listings})")

            results = []
            page = self._new_page()

            for i, url in enumerate(urls):
                try:
                    console.print(f"  [{i+1}/{len(urls)}] {url[:80]}...")
                    html = self.fetch_page(url, page)
                    raw_path = self.save_raw_page(url, html)
                    data = self.parse_listing_page(html, url)
                    data["listing_url"] = url
                    data["raw_page_path"] = raw_path
                    data["source_site"] = self.site_name
                    results.append(data)
                    self._delay()
                except Exception as e:
                    console.print(f"  [red]Failed: {e}[/]")
                    continue

            page.close()
            console.print(f"[green]{self.site_name}: scraped {len(results)} listings[/]")
            return results
        finally:
            self._close_browser()
