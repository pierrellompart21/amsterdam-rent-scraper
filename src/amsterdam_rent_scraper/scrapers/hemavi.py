"""Hemavi.com scraper - Swedish rental marketplace (JavaScript rendered)."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class HemaviScraper(PlaywrightBaseScraper):
    """Scraper for hemavi.com Swedish rental listings.

    Hemavi is a rental marketplace for Sweden.
    The site requires JavaScript rendering.
    """

    site_name = "hemavi"
    base_url = "https://hemavi.com"

    def _new_page(self) -> Page:
        """Create a new page with Swedish locale settings."""
        browser = self._get_browser()
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="sv-SE",
        )
        page = context.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self) -> str:
        """Build search URL for Stockholm area rentals."""
        return (
            f"{self.base_url}/bostader/hyresratt/stockholm"
            f"?minRent={self.min_price}&maxRent={self.max_price}"
        )

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []

        search_url = self.get_search_url()
        console.print(f"  Fetching: {search_url}")

        try:
            page.goto(search_url, wait_until="networkidle", timeout=60000)

            # Handle cookie consent
            try:
                consent_btn = page.locator('button:has-text("Acceptera"), button:has-text("Godkänn")')
                if consent_btn.count() > 0:
                    consent_btn.first.click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            page.wait_for_timeout(5000)

            # Scroll to load content
            prev_count = 0
            for scroll_attempt in range(10):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")
                links = [l for l in soup.find_all("a", href=True)
                        if "/bostad/" in l.get("href", "") or "/objekt/" in l.get("href", "")]

                current_count = len(links)
                if current_count == prev_count:
                    break
                prev_count = current_count

                if self.max_listings and current_count >= self.max_listings:
                    break

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Find listing links
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "/bostad/" in href or "/objekt/" in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            console.print(f"  Found {len(urls)} listing links")

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")

        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Hemavi listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Try JSON-LD structured data
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    if item.get("@type") in ["Apartment", "House", "Product", "Residence"]:
                        if "name" in item:
                            data["title"] = item["name"]
                        if "description" in item:
                            data["description"] = item["description"][:2000]
                        if "address" in item:
                            addr = item["address"]
                            if isinstance(addr, dict):
                                parts = []
                                if addr.get("streetAddress"):
                                    parts.append(addr["streetAddress"])
                                if addr.get("addressLocality"):
                                    parts.append(addr["addressLocality"])
                                if addr.get("postalCode"):
                                    data["postal_code"] = addr["postalCode"]
                                if parts:
                                    data["address"] = ", ".join(parts)
            except (json.JSONDecodeError, TypeError):
                continue

        # Title
        if "title" not in data:
            h1 = soup.select_one("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)

        if "title" not in data:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Price - Swedish format
        price_patterns = [
            r"(\d[\d\s]*)\s*kr\s*/\s*(?:mån|månad)",
            r"hyra[:\s]*(\d[\d\s]*)\s*kr",
            r"(\d[\d\s]*)\s*SEK",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 1000 <= price <= 50000:
                        data["price_sek"] = price
                        data["price_eur"] = round(price / 11.5, 2)
                        break
                except ValueError:
                    continue

        # Surface area
        surface_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m[²2]", full_text, re.IGNORECASE)
        if surface_match:
            try:
                data["surface_m2"] = float(surface_match.group(1).replace(",", "."))
            except ValueError:
                pass

        # Rooms
        room_match = re.search(r"(\d+)\s*rum", full_text, re.IGNORECASE)
        if room_match:
            try:
                data["rooms"] = int(room_match.group(1))
            except ValueError:
                pass

        # Swedish postal code
        if "postal_code" not in data:
            postal_match = re.search(r"\b(\d{3}\s?\d{2})\b", full_text)
            if postal_match:
                postal = postal_match.group(1).replace(" ", "")
                if postal.startswith("1"):
                    data["postal_code"] = f"{postal[:3]} {postal[3:]}"

        # Description
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        data["property_type"] = "Apartment"

        return data
