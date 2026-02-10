"""HomeQ.se scraper - Digital Swedish rental platform (JavaScript rendered)."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class HomeQScraper(PlaywrightBaseScraper):
    """Scraper for homeq.se Swedish rental listings.

    HomeQ is a digital rental platform with verified landlords.
    The site uses React and requires JavaScript rendering.

    URL patterns:
    - Search: https://www.homeq.se/sok-bostad?area=stockholm
    - Listing: https://www.homeq.se/bostad/{id}
    """

    site_name = "homeq"
    base_url = "https://www.homeq.se"

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
        base = f"{self.base_url}/sok-bostad"
        params = ["area=stockholm"]

        if self.min_price:
            params.append(f"minRent={self.min_price}")
        if self.max_price:
            params.append(f"maxRent={self.max_price}")

        return f"{base}?{'&'.join(params)}"

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs."""
        try:
            consent_selectors = [
                'button:has-text("Acceptera")',
                'button:has-text("Godkänn")',
            ]
            for selector in consent_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        page.wait_for_timeout(1000)
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        seen_ids = set()

        search_url = self.get_search_url()
        console.print(f"  Fetching: {search_url}")

        try:
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            self._handle_cookie_consent(page)
            page.wait_for_timeout(5000)

            # Scroll to load more
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # TODO: Adjust selector based on actual HomeQ HTML structure
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "/bostad/" in href:
                    listing_match = re.search(r"/bostad/([^/]+)", href)
                    if listing_match:
                        listing_id = listing_match.group(1)
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            full_url = urljoin(self.base_url, href)
                            urls.append(full_url)

            console.print(f"  Found {len(urls)} listing URLs")

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")

        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a HomeQ listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Title
        h1 = soup.select_one("h1")
        if h1:
            data["title"] = h1.get_text(strip=True)

        # Try JSON-LD
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    if item.get("@type") in ["Apartment", "House", "Residence"]:
                        if "name" in item:
                            data["title"] = item["name"]
                        if "description" in item:
                            data["description"] = item["description"][:2000]
            except (json.JSONDecodeError, TypeError):
                continue

        # Price
        price_patterns = [
            r"(\d[\d\s]*)\s*kr\s*/\s*m(?:ån|ånad)",
            r"hyra[:\s]*(\d[\d\s]*)\s*kr",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 1000 <= price <= 100000:
                        data["price_sek"] = price
                        data["price_eur"] = round(price / 11.5, 2)
                        break
                except ValueError:
                    continue

        # Surface area
        surface_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m[²2]", full_text)
        if surface_match:
            try:
                data["surface_m2"] = float(surface_match.group(1).replace(",", "."))
            except ValueError:
                pass

        # Rooms
        room_match = re.search(r"(\d+)\s*rum", full_text, re.IGNORECASE)
        if room_match:
            data["rooms"] = int(room_match.group(1))

        # Postal code
        postal_match = re.search(r"\b(\d{3})\s*(\d{2})\b", full_text)
        if postal_match:
            data["postal_code"] = f"{postal_match.group(1)} {postal_match.group(2)}"

        # Balcony
        if re.search(r"\bbalkong\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True

        # Description
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        data["property_type"] = "Apartment"
        return data
