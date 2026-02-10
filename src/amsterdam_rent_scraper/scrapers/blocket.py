"""Blocket.se scraper - Sweden's largest classifieds site (JavaScript rendered)."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class BlocketScraper(PlaywrightBaseScraper):
    """Scraper for blocket.se Swedish rental listings.

    Blocket is Sweden's largest classifieds site with a major rental section.
    The site is React-based and requires JavaScript rendering.
    """

    site_name = "blocket"
    base_url = "https://bostad.blocket.se"

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
        # Block images only
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self) -> str:
        """Build search URL for Stockholm area rentals."""
        # Blocket housing search for Stockholm
        # cid=20 is Stockholm region
        return (
            f"{self.base_url}/p2/sv/find"
            f"?cid=20&price_min={self.min_price}&price_max={self.max_price}"
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

            # Scroll to load more content
            prev_count = 0
            for scroll_attempt in range(10):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")
                # TODO: Update selector based on actual Blocket HTML structure
                links = soup.find_all("a", href=True)
                listing_links = [l for l in links if "/bostad/" in l.get("href", "") or "/home/" in l.get("href", "")]

                current_count = len(listing_links)
                if current_count == prev_count:
                    break
                prev_count = current_count

                if self.max_listings and current_count >= self.max_listings:
                    break

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Find listing links - TODO: refine selector based on actual structure
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "/bostad/" in href or "/home/" in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            console.print(f"  Found {len(urls)} listing links")

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")

        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Blocket listing page and extract data."""
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

        # Title from h1 or og:title
        if "title" not in data:
            h1 = soup.select_one("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)

        if "title" not in data:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Price - Swedish format: "X kr/mån" or "X SEK"
        price_patterns = [
            r"(\d[\d\s]*)\s*kr\s*/\s*(?:mån|månad)",
            r"hyra[:\s]*(\d[\d\s]*)\s*kr",
            r"(\d[\d\s]*)\s*SEK\s*/\s*(?:mån|månad)",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 1000 <= price <= 50000:  # SEK range
                        data["price_sek"] = price
                        # Convert to EUR (approximate rate)
                        data["price_eur"] = round(price / 11.5, 2)
                        break
                except ValueError:
                    continue

        # Surface area
        surface_patterns = [
            r"(\d+(?:[.,]\d+)?)\s*m[²2]",
            r"boarea[:\s]*(\d+(?:[.,]\d+)?)",
            r"storlek[:\s]*(\d+(?:[.,]\d+)?)",
        ]
        for pattern in surface_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                surface_str = match.group(1).replace(",", ".")
                try:
                    data["surface_m2"] = float(surface_str)
                    break
                except ValueError:
                    continue

        # Rooms - Swedish format: "X rum"
        room_patterns = [
            r"(\d+)\s*rum",
            r"(\d+)\s*rok",  # rum och kök
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["rooms"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Swedish postal code (5 digits, space after 3)
        if "postal_code" not in data:
            postal_match = re.search(r"\b(\d{3}\s?\d{2})\b", full_text)
            if postal_match:
                postal = postal_match.group(1).replace(" ", "")
                # Stockholm area codes start with 1
                if postal.startswith("1"):
                    data["postal_code"] = f"{postal[:3]} {postal[3:]}"

        # Description
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        data["property_type"] = "Apartment"

        return data
