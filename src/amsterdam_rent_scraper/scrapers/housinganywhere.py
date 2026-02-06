"""HousingAnywhere.com scraper - requires JavaScript for listings."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class HousingAnywhereScraper(PlaywrightBaseScraper):
    """Scraper for housinganywhere.com rental listings (JavaScript required)."""

    site_name = "housinganywhere"
    base_url = "https://housinganywhere.com"

    def get_search_url(self) -> str:
        """Build search URL for Amsterdam rentals."""
        return (
            f"{self.base_url}/s/Amsterdam--Netherlands/apartment"
            f"?priceMin={self.min_price}&priceMax={self.max_price}"
        )

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        search_url = self.get_search_url()
        console.print(f"  Fetching search page: {search_url[:80]}...")

        try:
            page.goto(search_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # HousingAnywhere uses infinite scroll, so scroll multiple times
            scroll_count = 3 if not self.test_mode else 1
            for i in range(scroll_count):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2500)
                console.print(f"  Scrolled {i+1}/{scroll_count}")

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # HousingAnywhere listing URLs: /Amsterdam--Netherlands/HASH
            # Property cards usually link to individual listings
            for link in soup.select('a[href*="/Amsterdam"]'):
                href = link.get("href", "")
                # Match listing detail URLs (have alphanumeric ID at end)
                if re.search(r"/Amsterdam[^/]*/[a-zA-Z0-9-]+$", href):
                    # Skip search/filter URLs
                    if not any(x in href for x in ["/s/", "?", "priceMin", "priceMax"]):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls:
                            urls.append(full_url)

            console.print(f"  Found {len(urls)} listing links")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/]")

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a HousingAnywhere listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Try JSON-LD structured data (HousingAnywhere often has this)
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                if isinstance(ld_data, dict):
                    if ld_data.get("@type") in ["Product", "Apartment", "Residence", "Accommodation"]:
                        if "name" in ld_data:
                            data["title"] = ld_data["name"]
                        if "description" in ld_data:
                            data["description"] = ld_data["description"][:2000]
                        if "address" in ld_data:
                            addr = ld_data["address"]
                            if isinstance(addr, dict):
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

        # Title fallback
        if "title" not in data:
            title_el = soup.select_one("h1, [class*='title']")
            if title_el:
                data["title"] = title_el.get_text(strip=True)

        # Price fallback
        if "price_eur" not in data:
            price_patterns = ['[class*="price"]', '.rent', '.cost']
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

        # Address fallback
        if "address" not in data:
            address_el = soup.select_one('[class*="address"], [class*="location"]')
            if address_el:
                data["address"] = address_el.get_text(strip=True)

        # Get full text for regex extraction
        full_text = soup.get_text()

        # Surface area
        surface_match = re.search(r"(\d+)\s*m[²2]", full_text)
        if surface_match:
            data["surface_m2"] = float(surface_match.group(1))

        # Rooms/bedrooms
        rooms_match = re.search(r"(\d+)\s*(?:bedroom|room|slaapkamer)", full_text, re.IGNORECASE)
        if rooms_match:
            data["rooms"] = int(rooms_match.group(1))

        # Bathrooms
        bath_match = re.search(r"(\d+)\s*(?:bathroom|badkamer)", full_text, re.IGNORECASE)
        if bath_match:
            data["bathrooms"] = int(bath_match.group(1))

        # Furnished status
        text_lower = full_text.lower()
        if "furnished" in text_lower:
            if "unfurnished" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"

        # Available dates
        avail_match = re.search(r"available\s*(?:from)?\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s*\d{4}|\d{1,2}[-/]\d{1,2}[-/]\d{4})", full_text, re.IGNORECASE)
        if avail_match:
            data["available_from"] = avail_match.group(1)

        # Property type
        type_match = re.search(r"(apartment|room|studio|house)", text_lower)
        if type_match:
            data["property_type"] = type_match.group(1).capitalize()

        # Description
        if "description" not in data:
            desc_el = soup.select_one('[class*="description"]')
            if desc_el:
                data["description"] = desc_el.get_text(strip=True)[:2000]

        # Features
        for item in soup.select('[class*="feature"], [class*="amenity"], li'):
            item_text = item.get_text(strip=True).lower()

            if "bedroom" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match:
                    data["bedrooms"] = int(match.group(1))

            if "bathroom" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match:
                    data["bathrooms"] = int(match.group(1))

            if "energy" in item_text:
                label_match = re.search(r"[A-G]\+*", item_text.upper())
                if label_match:
                    data["energy_label"] = label_match.group()

        # Postal code
        postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
        if postal_match:
            data["postal_code"] = postal_match.group(1).replace(" ", "")

        return data
