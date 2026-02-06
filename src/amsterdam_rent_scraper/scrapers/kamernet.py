"""Kamernet.nl scraper - requires JavaScript for listings."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class KamernetScraper(PlaywrightBaseScraper):
    """Scraper for kamernet.nl rental listings (JavaScript required)."""

    site_name = "kamernet"
    base_url = "https://kamernet.nl"

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Amsterdam rentals."""
        # Kamernet uses Dutch URLs: /huren/huurwoningen-amsterdam
        url = f"{self.base_url}/huren/huurwoningen-amsterdam"
        params = []
        if self.min_price:
            params.append(f"minRent={self.min_price}")
        if self.max_price:
            params.append(f"maxRent={self.max_price}")
        if page_num > 1:
            params.append(f"pageNo={page_num}")
        if params:
            url += "?" + "&".join(params)
        return url

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page_num = 1
        max_pages = 2 if self.test_mode else 10

        while page_num <= max_pages:
            search_url = self.get_search_url(page_num)
            console.print(f"  Fetching search page {page_num}: {search_url[:80]}...")

            try:
                page.goto(search_url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)

                # Scroll to load more
                for _ in range(2):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # Kamernet listing URLs: /huren/kamer-amsterdam/STREET/kamer-ID
                # or /huren/appartement-amsterdam/STREET/appartement-ID
                page_urls = []
                for link in soup.select('a[href*="/huren/"]'):
                    href = link.get("href", "")
                    # Match listing URLs with type-ID pattern
                    if re.search(r"/huren/(kamer|appartement|studio|woning)-amsterdam/[^/]+/(kamer|appartement|studio|woning)-\d+$", href):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls and full_url not in page_urls:
                            page_urls.append(full_url)

                if not page_urls:
                    console.print(f"  No listings found on page {page_num}")
                    break

                urls.extend(page_urls)
                console.print(f"  Page {page_num}: found {len(page_urls)} links")

                # Check for next page
                has_next = soup.select_one(f'a[href*="pageNo={page_num + 1}"]') or \
                          soup.select_one('.pagination .next:not(.disabled)')
                if not has_next:
                    break

                page_num += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page_num}: {e}[/]")
                break

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Kamernet listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Try JSON-LD structured data
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                if isinstance(ld_data, dict) and ld_data.get("@type") in ["Product", "Apartment", "Room"]:
                    if "name" in ld_data:
                        data["title"] = ld_data["name"]
                    if "description" in ld_data:
                        data["description"] = ld_data["description"][:2000]
            except (json.JSONDecodeError, TypeError):
                continue

        # Title - try multiple sources
        if "title" not in data:
            title_el = soup.select_one("h1, .room-title, .listing-title")
            if title_el:
                data["title"] = title_el.get_text(strip=True)

        # Fallback: derive title from URL
        # URL pattern: /huren/TYPE-amsterdam/STREET/TYPE-ID
        if "title" not in data or not data.get("title"):
            url_match = re.search(r"/huren/(\w+)-amsterdam/([^/]+)/", url)
            if url_match:
                prop_type = url_match.group(1).replace("-", " ").title()
                street = url_match.group(2).replace("-", " ").title()
                data["title"] = f"{prop_type} - {street}, Amsterdam"

        # Price - Kamernet shows monthly rent
        price_patterns = ['.rent-price', '.price', '[class*="price"]', '.monthly-rent']
        for pattern in price_patterns:
            for el in soup.select(pattern):
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
            if "price_eur" in data:
                break

        # Address/location
        address_patterns = ['.address', '.location', '[class*="address"]', '[class*="location"]']
        for pattern in address_patterns:
            el = soup.select_one(pattern)
            if el:
                data["address"] = el.get_text(strip=True)
                break

        # Fallback: derive address from URL
        if "address" not in data or not data.get("address"):
            url_match = re.search(r"/huren/\w+-amsterdam/([^/]+)/", url)
            if url_match:
                street = url_match.group(1).replace("-", " ").title()
                data["address"] = f"{street}, Amsterdam"

        # Get text for regex extraction
        full_text = soup.get_text()

        # Surface area
        surface_match = re.search(r"(\d+)\s*m[²2]", full_text)
        if surface_match:
            data["surface_m2"] = float(surface_match.group(1))

        # Rooms
        rooms_match = re.search(r"(\d+)\s*(?:room|kamer)", full_text, re.IGNORECASE)
        if rooms_match:
            data["rooms"] = int(rooms_match.group(1))

        # Property type from URL or page
        if "/kamer-" in url:
            data["property_type"] = "Room"
        elif "/appartement-" in url:
            data["property_type"] = "Apartment"
        elif "/studio-" in url:
            data["property_type"] = "Studio"
        elif "/woning-" in url:
            data["property_type"] = "House"

        # Furnished status
        text_lower = full_text.lower()
        if "furnished" in text_lower:
            if "unfurnished" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"
        elif "gemeubileerd" in text_lower:
            data["furnished"] = "Furnished"
        elif "gestoffeerd" in text_lower:
            data["furnished"] = "Upholstered"

        # Available from date
        avail_match = re.search(r"available\s*(?:from)?\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", text_lower)
        if avail_match:
            data["available_from"] = avail_match.group(1)

        # Description
        if "description" not in data:
            desc_el = soup.select_one('.description, .room-description, [class*="description"]')
            if desc_el:
                data["description"] = desc_el.get_text(strip=True)[:2000]

        # Features from detail items
        for item in soup.select('.detail-item, .feature, .spec, li'):
            item_text = item.get_text(strip=True).lower()

            if "bedroom" in item_text or "slaapkamer" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match:
                    data["bedrooms"] = int(match.group(1))

            if "bathroom" in item_text or "badkamer" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match:
                    data["bathrooms"] = int(match.group(1))

            if "energy" in item_text or "energie" in item_text:
                label_match = re.search(r"[A-G]\+*", item_text.upper())
                if label_match:
                    data["energy_label"] = label_match.group()

        # Postal code
        postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
        if postal_match:
            data["postal_code"] = postal_match.group(1).replace(" ", "")

        return data
