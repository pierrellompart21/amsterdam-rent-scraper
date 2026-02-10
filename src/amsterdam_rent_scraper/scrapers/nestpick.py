"""Nestpick.com scraper - International furnished apartment platform."""

import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class NestpickScraper(PlaywrightBaseScraper):
    """Scraper for nestpick.com furnished apartment listings.

    Nestpick is an international platform offering furnished apartments
    with flexible leases, popular with expats and professionals.

    URL patterns:
    - Search: https://www.nestpick.com/stockholm/
    - With filters: ?price_min=500&price_max=2000 (EUR)
    - Listing: /apartment/{slug}
    """

    site_name = "nestpick"
    base_url = "https://www.nestpick.com"

    def _new_page(self) -> Page:
        """Create a new page with English locale settings."""
        browser = self._get_browser()
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = context.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Stockholm furnished apartments."""
        base = f"{self.base_url}/stockholm/"
        params = {}
        # Nestpick uses EUR for price filters
        if self.min_price:
            # Convert SEK to EUR (approximate)
            params["price_min"] = int(self.min_price / 11.5)
        if self.max_price:
            params["price_max"] = int(self.max_price / 11.5)
        if page_num > 1:
            params["page"] = page_num
        if params:
            return f"{base}?{urlencode(params)}"
        return base

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs."""
        try:
            consent_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("OK")',
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
        """Scrape search results to get all listing URLs with pagination."""
        urls = []
        seen_ids = set()
        current_page = 1
        max_pages = 15

        console.print(f"  Starting search on {self.site_name}...")

        while current_page <= max_pages:
            try:
                page_url = self.get_search_url(current_page)
                console.print(f"  Fetching page {current_page}: {page_url}")

                page.goto(page_url, wait_until="networkidle", timeout=60000)

                if current_page == 1:
                    self._handle_cookie_consent(page)

                page.wait_for_timeout(3000)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # Find listing links - Nestpick uses /apartment/ or /room/ paths
                listing_links = soup.find_all("a", href=re.compile(r"/apartment/|/room/|/studio/"))

                if not listing_links:
                    console.print(f"  No listings found on page {current_page}")
                    break

                new_urls = 0
                for link in listing_links:
                    href = link.get("href", "")
                    # Extract slug as ID
                    id_match = re.search(r"/(apartment|room|studio)/([^/]+)", href)
                    if id_match:
                        listing_id = id_match.group(2)
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            full_url = urljoin(self.base_url, href)
                            urls.append(full_url)
                            new_urls += 1

                console.print(f"  Page {current_page}: Found {new_urls} new listings")

                if new_urls == 0:
                    break

                # Check for next page
                next_btn = soup.find("a", class_=re.compile(r"next|pagination"))
                next_link = soup.find("a", href=re.compile(rf"page={current_page + 1}"))
                if not next_btn and not next_link:
                    break

                current_page += 1

            except Exception as e:
                console.print(f"  [red]Error on page {current_page}: {e}[/]")
                break

        console.print(f"  Total: Found {len(urls)} listing URLs")
        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Nestpick listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Title
        title_tag = soup.find("h1")
        if title_tag:
            data["title"] = title_tag.get_text(strip=True)

        # Price - Nestpick shows EUR prices, also look for SEK
        # EUR pattern
        eur_match = re.search(r"€\s*(\d{1,3}(?:[.,]\d{3})*|\d+)", full_text)
        if eur_match:
            price_str = eur_match.group(1).replace(",", "").replace(".", "")
            try:
                price_eur = float(price_str)
                if 200 <= price_eur <= 10000:
                    data["price_eur"] = price_eur
                    data["price_sek"] = round(price_eur * 11.5, 2)
            except ValueError:
                pass

        # Also check for SEK prices
        if "price_sek" not in data:
            sek_match = re.search(r"(\d{1,3}(?:[\s,]\d{3})*)\s*(?:kr|SEK)", full_text)
            if sek_match:
                price_str = sek_match.group(1).replace(" ", "").replace(",", "")
                try:
                    price_sek = float(price_str)
                    if 3000 <= price_sek <= 100000:
                        data["price_sek"] = price_sek
                        data["price_eur"] = round(price_sek / 11.5, 2)
                except ValueError:
                    pass

        # Surface area
        surface_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|sqm|kvm)", full_text, re.IGNORECASE)
        if surface_match:
            try:
                data["surface_m2"] = float(surface_match.group(1).replace(",", "."))
            except ValueError:
                pass

        # Rooms/Bedrooms
        bedroom_match = re.search(r"(\d+)\s*(?:bedroom|bed|br)\b", full_text, re.IGNORECASE)
        if bedroom_match:
            try:
                data["bedrooms"] = int(bedroom_match.group(1))
                data["rooms"] = data["bedrooms"] + 1  # Assume living room
            except ValueError:
                pass

        # Address
        addr_tag = soup.find(class_=re.compile(r"address|location", re.IGNORECASE))
        if addr_tag:
            data["address"] = addr_tag.get_text(strip=True)

        # Furnished status - Nestpick is typically furnished
        data["furnished"] = "Furnished"

        # Features
        if re.search(r"\bbalcony\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True
        if re.search(r"\belevator|lift\b", full_text, re.IGNORECASE):
            data["has_elevator"] = True
        if re.search(r"\bparking|garage\b", full_text, re.IGNORECASE):
            data["has_parking"] = True

        # Available date
        if re.search(r"available\s*now|immediately", full_text, re.IGNORECASE):
            data["available_date"] = "Immediately"

        data["property_type"] = "Apartment"
        data["agency"] = "Nestpick"
        return data
