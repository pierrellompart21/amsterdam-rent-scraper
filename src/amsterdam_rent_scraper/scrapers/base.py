"""Base scraper class that all site-specific scrapers inherit from."""

import abc
import hashlib
import random
import time
from pathlib import Path

import httpx
from fake_useragent import UserAgent
from rich.console import Console
from tenacity import retry, stop_after_attempt, wait_exponential

from amsterdam_rent_scraper.config.settings import (
    MAX_RETRIES,
    RAW_PAGES_DIR,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
    TIMEOUT,
)

console = Console()
ua = UserAgent()


class BaseScraper(abc.ABC):
    """Abstract base for all rental site scrapers."""

    site_name: str = "unknown"

    def __init__(
        self, min_price: int = 1000, max_price: int = 2000, test_mode: bool = False
    ):
        self.min_price = min_price
        self.max_price = max_price
        self.test_mode = test_mode
        self.max_listings = 3 if test_mode else 10000
        RAW_PAGES_DIR.mkdir(parents=True, exist_ok=True)

    @abc.abstractmethod
    def get_listing_urls(self) -> list[str]:
        """Return list of individual listing URLs to scrape."""
        ...

    @abc.abstractmethod
    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a listing page and return raw extracted data."""
        ...

    def _delay(self):
        time.sleep(random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX))

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(min=2, max=30))
    def fetch_page(self, url: str) -> str:
        """Fetch a page with retry logic and random user agent."""
        headers = {
            "User-Agent": ua.random,
            "Accept-Language": "en-US,en;q=0.9,nl;q=0.8",
        }
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    def save_raw_page(self, url: str, html: str) -> str:
        """Save raw HTML to disk, return the file path."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"{self.site_name}_{url_hash}.html"
        path = RAW_PAGES_DIR / filename
        path.write_text(html, encoding="utf-8")
        return str(path)

    def scrape_all(self) -> list[dict]:
        """Full scrape pipeline: get URLs → fetch each → parse → return raw dicts."""
        console.print(f"[bold cyan]Scraping {self.site_name}...[/]")
        urls = self.get_listing_urls()
        if self.test_mode:
            urls = urls[: self.max_listings]
        console.print(f"  Found {len(urls)} listing URLs (limit: {self.max_listings})")

        results = []
        for i, url in enumerate(urls):
            try:
                console.print(f"  [{i+1}/{len(urls)}] {url[:80]}...")
                html = self.fetch_page(url)
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

        console.print(f"[green]{self.site_name}: scraped {len(results)} listings[/]")
        return results
