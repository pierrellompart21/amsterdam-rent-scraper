"""Rentumo.se scraper - Swedish rental aggregator (server-rendered)."""

import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class RentumoScraper(PlaywrightBaseScraper):
    """Scraper for rentumo.se Swedish rental listings.

    Rentumo is a rental aggregator that aggregates listings from multiple
    Swedish rental platforms including Qasa, Blocket, and others.
    The site is server-rendered with Turbo/Rails and works well with simple
    HTTP requests.

    URL patterns:
    - Search: https://rentumo.se/en/rentals/stockholm?min_rent=10000&max_rent=25000
    - Listing: https://rentumo.se/en/listings/{street}-{city}-{id}
    """

    site_name = "rentumo"
    base_url = "https://rentumo.se"

    def _new_page(self) -> Page:
        """Create a new page with settings."""
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

    def get_search_url(self) -> str:
        """Build search URL for Stockholm area rentals with price filter."""
        base = f"{self.base_url}/en/rentals/stockholm"
        params = {}
        if self.min_price:
            params["min_rent"] = int(self.min_price)
        if self.max_price:
            params["max_rent"] = int(self.max_price)
        if params:
            return f"{base}?{urlencode(params)}"
        return base

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs."""
        try:
            consent_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Acceptera")',
                'button:has-text("Allow")',
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
        """Scrape search results to get all listing URLs with pagination."""
        urls = []
        seen_ids = set()
        current_page = 1
        max_pages = 10  # Limit pagination to avoid infinite loops

        search_url = self.get_search_url()
        console.print(f"  Fetching: {search_url}")

        while current_page <= max_pages:
            try:
                # Add page parameter for pagination
                if current_page > 1:
                    page_url = f"{search_url}&page={current_page}" if "?" in search_url else f"{search_url}?page={current_page}"
                else:
                    page_url = search_url

                page.goto(page_url, wait_until="networkidle", timeout=60000)

                if current_page == 1:
                    self._handle_cookie_consent(page)

                page.wait_for_timeout(3000)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # Find listing cards - they have data-listing-id attribute
                listing_cards = soup.find_all(attrs={"data-listing-id": True})

                if not listing_cards:
                    console.print(f"  No listings found on page {current_page}")
                    break

                new_urls = 0
                for card in listing_cards:
                    listing_id = card.get("data-listing-id")
                    if listing_id and listing_id not in seen_ids:
                        seen_ids.add(listing_id)
                        # Find the link within or near the card
                        link = card.find("a", href=re.compile(r"/en/listings/|/hyresbostad/"))
                        if link:
                            href = link.get("href", "")
                            full_url = urljoin(self.base_url, href)
                            # Normalize to English URL
                            if "/hyresbostad/" in full_url:
                                full_url = full_url.replace("/hyresbostad/", "/en/listings/")
                            urls.append(full_url)
                            new_urls += 1

                console.print(f"  Page {current_page}: Found {new_urls} new listings")

                if new_urls == 0:
                    # No new listings found, stop pagination
                    break

                # Check for next page link
                next_link = soup.find("link", rel="next")
                if not next_link:
                    break

                current_page += 1

            except Exception as e:
                console.print(f"  [red]Error on page {current_page}: {e}[/]")
                break

        console.print(f"  Total: Found {len(urls)} listing URLs")
        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Rentumo listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Title from og:title or page title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            data["title"] = og_title["content"]
        else:
            title_tag = soup.find("title")
            if title_tag:
                # Remove "| Rentumo" suffix
                title = title_tag.get_text(strip=True)
                title = re.sub(r"\s*\|\s*Rentumo$", "", title)
                data["title"] = title

        # Description from meta description or og:description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            data["description"] = meta_desc["content"][:2000]

        # Extract address from URL pattern: /listings/{street}-{city}-{id}
        url_match = re.search(r"/(?:en/)?listings/([^/]+)-(\d+)$", url)
        if url_match:
            slug = url_match.group(1)
            # Convert slug to address (e.g., "bohusgatan-stockholm" -> "Bohusgatan, Stockholm")
            parts = slug.rsplit("-", 1)
            if len(parts) == 2:
                street = parts[0].replace("-", " ").title()
                city = parts[1].title()
                data["address"] = f"{street}, {city}"

        # Price - look for patterns like "13,800 kr" or "13 800 kr"
        price_patterns = [
            r"(\d{1,3}(?:[,\s]\d{3})+)\s*kr",  # 13,800 kr or 13 800 kr
            r"(\d+)\s*kr\s*/\s*m(?:ån|onth)",  # X kr/month
            r"price[=:]\s*(\d+(?:,\d+)?)",     # price=13800
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(",", "").replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 1000 <= price <= 100000:
                        data["price_sek"] = price
                        data["price_eur"] = round(price / 11.5, 2)
                        break
                except ValueError:
                    continue

        # Try to extract price from og:image URL which contains price info
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content") and "price_sek" not in data:
            img_url = og_image["content"]
            # Extract price from URL like &price=13%2C800 (URL encoded 13,800)
            price_match = re.search(r"price=(\d+(?:%2C\d+)?)", img_url)
            if price_match:
                price_str = price_match.group(1).replace("%2C", "")
                try:
                    price = float(price_str)
                    if 1000 <= price <= 100000:
                        data["price_sek"] = price
                        data["price_eur"] = round(price / 11.5, 2)
                except ValueError:
                    pass

        # Surface area - Swedish "kvm" or "m²"
        surface_patterns = [
            r"(\d+(?:[.,]\d+)?)\s*(?:kvm|m²|m2|sqm)",
            r"(\d+(?:[.,]\d+)?)\s*kvadratmeter",
        ]
        for pattern in surface_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["surface_m2"] = float(match.group(1).replace(",", "."))
                    break
                except ValueError:
                    continue

        # Rooms/Bedrooms - from title or content
        room_patterns = [
            r"(\d+)[- ]?(?:bedroom|rum|rok)\b",
            r"(\d+):a\b",  # Swedish "2:a" = 2-room apartment
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["rooms"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Postal code (Swedish format: XXX XX)
        postal_match = re.search(r"\b(\d{3})\s*(\d{2})\b", full_text)
        if postal_match:
            data["postal_code"] = f"{postal_match.group(1)} {postal_match.group(2)}"

        # Balcony
        if re.search(r"\b(?:balkong|balcony)\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True

        # Elevator
        if re.search(r"\b(?:hiss|elevator|lift)\b", full_text, re.IGNORECASE):
            data["has_elevator"] = True

        # Furnished
        if re.search(r"\b(?:möblerad|furnished|möbler)\b", full_text, re.IGNORECASE):
            data["is_furnished"] = True

        # Floor
        floor_match = re.search(r"(?:våning|floor)[:\s]*(\d+)", full_text, re.IGNORECASE)
        if floor_match:
            data["floor"] = floor_match.group(1)

        data["property_type"] = "Apartment"
        return data
