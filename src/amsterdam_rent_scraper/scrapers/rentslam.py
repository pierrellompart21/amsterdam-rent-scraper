"""Rentslam.com scraper - aggregator site, requires JavaScript."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class RentslamScraper(PlaywrightBaseScraper):
    """Scraper for rentslam.com rental listings (aggregator, JavaScript required)."""

    site_name = "rentslam"
    base_url = "https://rentslam.com"

    def get_search_url(self) -> str:
        """Build search URL for Amsterdam rentals."""
        # Rentslam filters in URL
        return (
            f"{self.base_url}/en/apartments/amsterdam"
            f"?min_price={self.min_price}&max_price={self.max_price}"
        )

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        search_url = self.get_search_url()
        console.print(f"  Fetching search page: {search_url[:80]}...")

        try:
            page.goto(search_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # Scroll to load more listings
            scroll_count = 3 if not self.test_mode else 1
            for i in range(scroll_count):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Rentslam listing URLs typically /en/listing/ID or similar
            for link in soup.select('a[href*="/listing/"], a[href*="/apartment/"], a[href*="/property/"]'):
                href = link.get("href", "")
                if re.search(r"/(listing|apartment|property)/\w+", href):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            # Also try card/item links
            for link in soup.select('[class*="card"] a, [class*="item"] a, [class*="listing"] a'):
                href = link.get("href", "")
                if href and href.startswith("/") and "/search" not in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            console.print(f"  Found {len(urls)} listing links")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/]")

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Rentslam listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Rentslam is an aggregator, might redirect to source site
        # Extract what we can from the page

        # Try JSON-LD
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                if isinstance(ld_data, dict):
                    if "name" in ld_data:
                        data["title"] = ld_data["name"]
                    if "description" in ld_data:
                        data["description"] = ld_data["description"][:2000]
                    if "address" in ld_data and isinstance(ld_data["address"], dict):
                        addr = ld_data["address"]
                        parts = [addr.get("streetAddress", ""),
                                addr.get("postalCode", ""),
                                addr.get("addressLocality", "")]
                        data["address"] = " ".join(p for p in parts if p)
                    if "offers" in ld_data and isinstance(ld_data["offers"], dict):
                        if "price" in ld_data["offers"]:
                            try:
                                data["price_eur"] = float(ld_data["offers"]["price"])
                            except (ValueError, TypeError):
                                pass
            except (json.JSONDecodeError, TypeError):
                continue

        # Title
        if "title" not in data:
            title_el = soup.select_one("h1, [class*='title']")
            if title_el:
                data["title"] = title_el.get_text(strip=True)

        # Price
        if "price_eur" not in data:
            for el in soup.select('[class*="price"], .rent, .cost'):
                price_text = el.get_text(strip=True)
                price_match = re.search(r"€\s*([\d.,]+)", price_text)
                if price_match:
                    price_str = price_match.group(1).replace(".", "").replace(",", "")
                    try:
                        price = float(price_str)
                        if 100 <= price <= 10000:
                            data["price_eur"] = price
                            break
                    except ValueError:
                        continue

        # Address
        if "address" not in data:
            address_el = soup.select_one('[class*="address"], [class*="location"]')
            if address_el:
                data["address"] = address_el.get_text(strip=True)

        # Full text extraction
        full_text = soup.get_text()

        # Surface
        surface_match = re.search(r"(\d+)\s*m[²2]", full_text)
        if surface_match:
            data["surface_m2"] = float(surface_match.group(1))

        # Rooms
        rooms_match = re.search(r"(\d+)\s*(?:bedroom|room|kamer)", full_text, re.IGNORECASE)
        if rooms_match:
            data["rooms"] = int(rooms_match.group(1))

        # Bathrooms
        bath_match = re.search(r"(\d+)\s*(?:bathroom|badkamer)", full_text, re.IGNORECASE)
        if bath_match:
            data["bathrooms"] = int(bath_match.group(1))

        # Furnished
        text_lower = full_text.lower()
        if "furnished" in text_lower or "gemeubileerd" in text_lower:
            if "unfurnished" in text_lower or "ongemeubileerd" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"

        # Description
        if "description" not in data:
            desc_el = soup.select_one('[class*="description"], .content')
            if desc_el:
                data["description"] = desc_el.get_text(strip=True)[:2000]

        # Postal code
        postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
        if postal_match:
            data["postal_code"] = postal_match.group(1).replace(" ", "")

        # Source site (aggregator might show this)
        source_match = re.search(r"source[:\s]*([\w.]+)", text_lower)
        if source_match:
            data["original_source"] = source_match.group(1)

        return data
