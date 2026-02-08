"""Stealth base scraper class for bypassing bot detection.

This module provides a StealthBaseScraper that uses undetected-chromedriver
instead of Playwright, designed for sites with aggressive anti-bot measures.

Usage:
    class MySiteStealth(StealthBaseScraper):
        site_name = "mysite"

        def get_listing_urls(self, browser: StealthBrowser) -> list[str]:
            # Implementation using browser.get(), browser.page_source, etc.
            ...

        def parse_listing_page(self, html: str, url: str) -> dict:
            # Same as PlaywrightBaseScraper
            ...
"""

import abc
import hashlib
import random
import time
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from amsterdam_rent_scraper.config.settings import (
    RAW_PAGES_DIR,
    REQUEST_DELAY_MAX,
    REQUEST_DELAY_MIN,
)
from amsterdam_rent_scraper.utils.stealth_browser import (
    StealthBrowser,
    is_stealth_available,
)

console = Console()


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


class StealthBaseScraper(abc.ABC):
    """Abstract base for scrapers that need stealth mode to bypass anti-bot measures.

    This scraper uses undetected-chromedriver instead of Playwright for better
    bot detection avoidance. It includes human-like behavior patterns.
    """

    site_name: str = "unknown"

    # Stealth-specific settings
    STEALTH_DELAY_MIN = 3.0  # Longer delays for stealth
    STEALTH_DELAY_MAX = 7.0

    def __init__(
        self,
        min_price: int = 1000,
        max_price: int = 2000,
        test_mode: bool = False,
        max_listings: int = None,
        headless: bool = True,
        locale: str = "en-US",
    ):
        self.min_price = min_price
        self.max_price = max_price
        self.test_mode = test_mode
        self.headless = headless
        self.locale = locale

        # Priority: explicit max_listings > test_mode default > unlimited
        if max_listings is not None:
            self.max_listings = max_listings
        elif test_mode:
            self.max_listings = 3
        else:
            self.max_listings = None  # None = no limit

        RAW_PAGES_DIR.mkdir(parents=True, exist_ok=True)
        self._browser: Optional[StealthBrowser] = None

    @abc.abstractmethod
    def get_listing_urls(self, browser: StealthBrowser) -> list[str]:
        """Return list of individual listing URLs to scrape.

        Args:
            browser: StealthBrowser instance for navigation

        Returns:
            List of listing URLs
        """
        ...

    @abc.abstractmethod
    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a listing page and return raw extracted data.

        Args:
            html: The page HTML source
            url: The page URL

        Returns:
            Dictionary with extracted listing data
        """
        ...

    def _delay(self, min_delay: float = None, max_delay: float = None):
        """Wait with human-like random delay."""
        min_d = min_delay or self.STEALTH_DELAY_MIN
        max_d = max_delay or self.STEALTH_DELAY_MAX
        time.sleep(random.uniform(min_d, max_d))

    def _get_browser(self) -> StealthBrowser:
        """Get or create a stealth browser instance."""
        if self._browser is None:
            if not is_stealth_available():
                raise ImportError(
                    f"Stealth mode for {self.site_name} requires 'undetected-chromedriver'. "
                    "Install with: pip install undetected-chromedriver"
                )
            self._browser = StealthBrowser(
                headless=self.headless,
                locale=self.locale,
                random_delays=True,
            )
            self._browser._start()
        return self._browser

    def _close_browser(self):
        """Close browser and cleanup."""
        if self._browser:
            self._browser.close()
            self._browser = None

    def fetch_page(
        self,
        url: str,
        browser: StealthBrowser = None,
        wait_selector: str = None,
        scroll: bool = True,
    ) -> str:
        """Fetch a page with stealth behavior.

        Args:
            url: URL to fetch
            browser: Optional browser instance (creates new if not provided)
            wait_selector: Optional CSS selector to wait for
            scroll: Whether to perform human-like scrolling

        Returns:
            The page HTML source
        """
        close_browser = browser is None
        if browser is None:
            browser = self._get_browser()

        try:
            browser.get(url, wait_for_selector=wait_selector)

            # Human-like scrolling
            if scroll:
                browser.human_scroll(scroll_count=random.randint(2, 4))

            # Random mouse movement
            if random.random() < 0.3:
                browser.random_mouse_movement()

            return browser.page_source
        finally:
            if close_browser:
                browser.close()

    def save_raw_page(self, url: str, html: str) -> str:
        """Save raw HTML to disk, return the file path."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"{self.site_name}_stealth_{url_hash}.html"
        path = RAW_PAGES_DIR / filename
        path.write_text(html, encoding="utf-8")
        return str(path)

    def scrape_all(self) -> list[dict]:
        """Full scrape pipeline: get URLs -> fetch each -> parse -> return raw dicts."""
        console.print(f"[bold magenta]Scraping {self.site_name} (Stealth Mode)...[/]")

        if not is_stealth_available():
            console.print(
                f"[red]{self.site_name}: Stealth mode unavailable. "
                "Install with: pip install undetected-chromedriver[/]"
            )
            return []

        try:
            browser = self._get_browser()

            # Get listing URLs with stealth browser
            urls = self.get_listing_urls(browser)

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
                task = progress.add_task(f"{self.site_name} (stealth)", total=len(urls))

                for url in urls:
                    try:
                        html = self.fetch_page(url, browser)
                        raw_path = self.save_raw_page(url, html)
                        data = self.parse_listing_page(html, url)
                        data["listing_url"] = url
                        data["raw_page_path"] = raw_path
                        data["source_site"] = self.site_name
                        data["_stealth_mode"] = True  # Mark as stealth-scraped
                        results.append(data)
                        self._delay()
                    except Exception as e:
                        failed += 1
                        console.print(f"  [red]Failed ({url[:50]}...): {e}[/]")
                    finally:
                        progress.advance(task)

            status = "[green]" if failed == 0 else "[yellow]"
            console.print(
                f"{status}{self.site_name} (stealth): scraped {len(results)} listings"
                + (f" ({failed} failed)" if failed else "")
                + "[/]"
            )
            return results
        except Exception as e:
            console.print(f"[red]{self.site_name} stealth error: {e}[/]")
            return []
        finally:
            self._close_browser()
