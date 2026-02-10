"""Bostadslistan.se scraper - Swedish rental listing aggregator with 2000+ listings."""

import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class BostadslistanScraper(PlaywrightBaseScraper):
    """Scraper for bostadslistan.se rental listings.

    Bostadslistan is a Swedish rental aggregator with over 2000 apartment
    listings in Stockholm. The site aggregates listings from multiple sources.

    URL patterns:
    - Search: https://bostadslistan.se/en/apartment-for-rent/stockholm
    - With filters: ?min_rent=10000&max_rent=25000
    """

    site_name = "bostadslistan"
    base_url = "https://bostadslistan.se"

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

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Stockholm area rentals with price filter."""
        base = f"{self.base_url}/en/apartment-for-rent/stockholm"
        params = {}
        if self.min_price:
            params["min_rent"] = int(self.min_price)
        if self.max_price:
            params["max_rent"] = int(self.max_price)
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
                'button:has-text("Acceptera")',
                'button:has-text("OK")',
                'button:has-text("I agree")',
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
        max_pages = 20  # Many listings available

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

                # Find listing links - typically /apartment/stockholm/...
                listing_links = soup.find_all("a", href=re.compile(r"/apartment/|/lagenhet/"))

                if not listing_links:
                    console.print(f"  No listings found on page {current_page}")
                    break

                new_urls = 0
                for link in listing_links:
                    href = link.get("href", "")
                    # Skip if it's just the search page
                    if "/apartment-for-rent/" in href or href.count("/") < 3:
                        continue
                    # Extract ID to deduplicate
                    id_match = re.search(r"/(\d+)/?$|/([a-zA-Z0-9-]+)/?$", href)
                    if id_match:
                        listing_id = id_match.group(1) or id_match.group(2)
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            full_url = urljoin(self.base_url, href)
                            urls.append(full_url)
                            new_urls += 1

                console.print(f"  Page {current_page}: Found {new_urls} new listings")

                if new_urls == 0:
                    break

                # Check for next page
                next_btn = soup.find("a", string=re.compile(r"Next|Nästa", re.IGNORECASE))
                next_page_link = soup.find("a", href=re.compile(rf"page={current_page + 1}"))

                if not next_btn and not next_page_link:
                    break

                current_page += 1

            except Exception as e:
                console.print(f"  [red]Error on page {current_page}: {e}[/]")
                break

        console.print(f"  Total: Found {len(urls)} listing URLs")
        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Bostadslistan listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Title from h1 or og:title
        title_tag = soup.find("h1")
        if title_tag:
            data["title"] = title_tag.get_text(strip=True)
        else:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Price - Swedish format: "XX XXX kr" or "XX XXX SEK"
        price_patterns = [
            r"(\d{1,3}(?:[\s\u00a0]\d{3})*)\s*(?:kr|SEK)(?:/månad|/mån|/month)?",
            r"(?:Hyra|Rent)[:\s]*(\d{1,3}(?:[\s\u00a0]\d{3})*)",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 3000 <= price <= 100000:
                        data["price_sek"] = price
                        data["price_eur"] = round(price / 11.5, 2)
                        break
                except ValueError:
                    continue

        # Surface area
        surface_patterns = [
            r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|kvm)",
            r"(?:Size|Storlek|Area)[:\s]*(\d+)",
        ]
        for pattern in surface_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["surface_m2"] = float(match.group(1).replace(",", "."))
                    break
                except ValueError:
                    continue

        # Rooms
        room_patterns = [
            r"(\d+)\s*(?:rum|rok|rooms?)\b",
            r"(\d+)\s*r\s*o\s*k\b",
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["rooms"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Address from meta or page content
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            # Often contains address info
            desc = og_desc["content"]
            addr_match = re.search(r"([A-ZÄÖÅ][a-zäöå]+(?:gatan|vägen|gränd|plan)\s*\d*)", desc)
            if addr_match:
                data["address"] = f"{addr_match.group(1)}, Stockholm"

        # Postal code
        postal_match = re.search(r"\b(\d{3})\s*(\d{2})\b", full_text)
        if postal_match:
            data["postal_code"] = f"{postal_match.group(1)} {postal_match.group(2)}"

        # Features
        if re.search(r"\bbalkong|balcony\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True
        if re.search(r"\bhiss|elevator\b", full_text, re.IGNORECASE):
            data["has_elevator"] = True
        if re.search(r"\bmöbler|furnished\b", full_text, re.IGNORECASE):
            data["is_furnished"] = True

        data["property_type"] = "Apartment"
        return data
