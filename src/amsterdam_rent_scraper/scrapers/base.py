"""Base scraper class that all site-specific scrapers inherit from."""

import abc
import hashlib
import random
import time
from pathlib import Path

import httpx
from fake_useragent import UserAgent
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
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


def create_scraping_progress() -> Progress:
    """Create a rich progress bar for scraping."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


class BaseScraper(abc.ABC):
    """Abstract base for all rental site scrapers."""

    site_name: str = "unknown"

    def __init__(
        self,
        min_price: int = 1000,
        max_price: int = 2000,
        test_mode: bool = False,
        max_listings: int = None,
        location: str = "amsterdam",
    ):
        self.min_price = min_price
        self.max_price = max_price
        self.test_mode = test_mode
        self.location = location
        # Priority: explicit max_listings > test_mode default > unlimited
        if max_listings is not None:
            self.max_listings = max_listings
        elif test_mode:
            self.max_listings = 3
        else:
            self.max_listings = None  # None = no limit (paginate until exhausted)
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
        # Apply max_listings limit if set
        if self.max_listings is not None:
            urls = urls[: self.max_listings]
            console.print(f"  Found {len(urls)} listing URLs (limit: {self.max_listings})")
        else:
            console.print(f"  Found {len(urls)} listing URLs (no limit)")

        if not urls:
            console.print(f"[yellow]{self.site_name}: no listings found[/]")
            return []

        results = []
        failed = 0

        with create_scraping_progress() as progress:
            task = progress.add_task(f"{self.site_name}", total=len(urls))

            for url in urls:
                try:
                    html = self.fetch_page(url)
                    raw_path = self.save_raw_page(url, html)
                    data = self.parse_listing_page(html, url)
                    data["listing_url"] = url
                    data["raw_page_path"] = raw_path
                    data["source_site"] = self.site_name
                    results.append(data)
                    self._delay()
                except Exception as e:
                    failed += 1
                    console.print(f"  [red]Failed ({url[:50]}...): {e}[/]")
                finally:
                    progress.advance(task)

        status = "[green]" if failed == 0 else "[yellow]"
        console.print(f"{status}{self.site_name}: scraped {len(results)} listings" + (f" ({failed} failed)" if failed else "") + "[/]")
        return results
