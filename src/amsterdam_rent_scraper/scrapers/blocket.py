"""Blocket.se scraper - Sweden's largest classifieds site (JavaScript rendered)."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class BlocketScraper(PlaywrightBaseScraper):
    """Scraper for blocket.se Swedish rental listings.

    Blocket is Sweden's largest classifieds site with a huge rental section.
    The site uses React and requires JavaScript rendering.

    URL patterns:
    - Search: https://www.blocket.se/annonser/stockholm/bostad/lagenheter?cg=3020&r=11
    - Listing: https://www.blocket.se/annons/stockholm/.../{id}
    """

    site_name = "blocket"
    base_url = "https://www.blocket.se"

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
        # Block images only (keep scripts/CSS for React rendering)
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Stockholm area rentals."""
        # cg=3020 is apartments for rent, r=11 is Stockholm region
        base = f"{self.base_url}/annonser/stockholm/bostad/lagenheter"
        params = ["cg=3020", "r=11", "f=p", "f=c"]  # f=p=private, f=c=company

        # Price filter (in SEK)
        if self.min_price:
            params.append(f"ps={self.min_price}")
        if self.max_price:
            params.append(f"pe={self.max_price}")

        # Pagination
        if page_num > 1:
            params.append(f"page={page_num}")

        return f"{base}?{'&'.join(params)}"

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs."""
        try:
            consent_selectors = [
                'button:has-text("Acceptera alla")',
                'button:has-text("Godkänn alla")',
                'button:has-text("Accept all")',
                '#onetrust-accept-btn-handler',
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

        search_url = self.get_search_url(page_num=1)
        console.print(f"  Fetching: {search_url}")

        try:
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            self._handle_cookie_consent(page)
            page.wait_for_timeout(5000)

            # TODO: Determine pagination from page content
            max_pages = 5  # Start with limited pages

            for page_num in range(1, max_pages + 1):
                if page_num > 1:
                    page_url = self.get_search_url(page_num=page_num)
                    page.goto(page_url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(3000)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # TODO: Adjust selector based on actual Blocket HTML structure
                # Blocket listing links typically contain /annons/ and a numeric ID
                page_urls = []
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    # Match listing URLs with pattern /annons/{region}/{category}/{id}
                    if "/annons/" in href and re.search(r"/\d{5,}", href):
                        listing_match = re.search(r"/(\d{5,})", href)
                        if listing_match:
                            listing_id = listing_match.group(1)
                            if listing_id not in seen_ids:
                                seen_ids.add(listing_id)
                                full_url = urljoin(self.base_url, href)
                                page_urls.append(full_url.split("?")[0])

                console.print(f"  Page {page_num}: found {len(page_urls)} new listings")
                urls.extend(page_urls)

                if self.max_listings and len(urls) >= self.max_listings:
                    break

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")

        console.print(f"  Total: {len(urls)} listing URLs found")
        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Blocket listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Title
        h1 = soup.select_one("h1")
        if h1:
            data["title"] = h1.get_text(strip=True)

        # Try JSON-LD structured data
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    if item.get("@type") in ["Apartment", "House", "Product", "RealEstateListing"]:
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

        # Price - Swedish format: "X kr/mån" or "X SEK/mån"
        price_patterns = [
            r"(\d[\d\s]*)\s*kr\s*/\s*m(?:ån|ånad)",
            r"(\d[\d\s]*)\s*SEK\s*/\s*m(?:ån|ånad)",
            r"hyra[:\s]*(\d[\d\s]*)\s*kr",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 1000 <= price <= 100000:  # SEK range
                        data["price_sek"] = price
                        # Convert to EUR (approximate)
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

        # Rooms - Swedish format: "X rum" or "Xr"
        room_patterns = [
            r"(\d+)\s*rum",
            r"(\d+)\s*r\b",
            r"(\d+)\s*rok\b",  # rum och kök
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["rooms"] = int(match.group(1))
                break

        # Swedish postal code (5 digits, often written as XXX XX)
        postal_match = re.search(r"\b(\d{3})\s*(\d{2})\b", full_text)
        if postal_match:
            data["postal_code"] = f"{postal_match.group(1)} {postal_match.group(2)}"

        # Floor
        floor_match = re.search(r"(\d+)\s*(?:våning|tr|trappor)", full_text, re.IGNORECASE)
        if floor_match:
            data["floor"] = floor_match.group(1)

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
