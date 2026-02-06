"""Roofz.nl scraper - requires JavaScript for listings."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class RoofzScraper(PlaywrightBaseScraper):
    """Scraper for roofz.nl rental listings (JavaScript required)."""

    site_name = "roofz"
    base_url = "https://roofz.nl"

    def get_search_url(self) -> str:
        """Build search URL for Amsterdam rentals."""
        # Roofz has English version
        return f"{self.base_url}/en/rent/amsterdam"

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        search_url = self.get_search_url()
        console.print(f"  Fetching search page: {search_url}")

        try:
            page.goto(search_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # Scroll to load listings
            scroll_count = 3 if not self.test_mode else 1
            for i in range(scroll_count):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Roofz listing URLs: /en/property/ID or /en/rent/amsterdam/ID
            for link in soup.select('a[href*="/property/"], a[href*="/rent/amsterdam/"]'):
                href = link.get("href", "")
                # Skip search page itself
                if href.endswith("/amsterdam") or href.endswith("/amsterdam/"):
                    continue
                # Match property URLs
                if re.search(r"/(property|rent/amsterdam)/[a-zA-Z0-9-]+$", href):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            # Also try card-based links
            for card in soup.select('[class*="card"], [class*="listing"], [class*="property"]'):
                link = card.select_one('a')
                if link:
                    href = link.get("href", "")
                    if href and "/rent/" in href and href not in ["/en/rent/amsterdam", "/en/rent/amsterdam/"]:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls:
                            urls.append(full_url)

            console.print(f"  Found {len(urls)} listing links")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/]")

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Roofz listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

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
                        if addr.get("postalCode"):
                            data["postal_code"] = addr["postalCode"].replace(" ", "")
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
            for el in soup.select('[class*="price"], .rent'):
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

        # Full text for regex
        full_text = soup.get_text()

        # Surface
        surface_match = re.search(r"(\d+)\s*m[²2]", full_text)
        if surface_match:
            data["surface_m2"] = float(surface_match.group(1))

        # Rooms
        rooms_match = re.search(r"(\d+)\s*(?:bedroom|room|kamer|slaapkamer)", full_text, re.IGNORECASE)
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
        elif "gestoffeerd" in text_lower:
            data["furnished"] = "Upholstered"

        # Energy label
        energy_match = re.search(r"energy\s*(?:label|rating)?[:\s]*([A-G]\+*)", full_text, re.IGNORECASE)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Description
        if "description" not in data:
            desc_el = soup.select_one('[class*="description"], .content')
            if desc_el:
                data["description"] = desc_el.get_text(strip=True)[:2000]

        # Features from lists
        for item in soup.select('li, [class*="feature"], [class*="spec"]'):
            item_text = item.get_text(strip=True).lower()

            if "bedroom" in item_text or "slaapkamer" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match and "bedrooms" not in data:
                    data["bedrooms"] = int(match.group(1))

            if "bathroom" in item_text or "badkamer" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match and "bathrooms" not in data:
                    data["bathrooms"] = int(match.group(1))

        # Postal code
        if "postal_code" not in data:
            postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
            if postal_match:
                data["postal_code"] = postal_match.group(1).replace(" ", "")

        return data
