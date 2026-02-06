"""Huurstunt.nl scraper - requires JavaScript for listings to load."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class HuurstuntScraper(PlaywrightBaseScraper):
    """Scraper for huurstunt.nl rental listings (JavaScript required)."""

    site_name = "huurstunt"
    base_url = "https://www.huurstunt.nl"

    def get_search_url(self) -> str:
        """Build search URL for Amsterdam rentals."""
        # Huurstunt doesn't support price filtering in URL, only city
        return f"{self.base_url}/huren/amsterdam/"

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        search_url = self.get_search_url()
        console.print(f"  Fetching search page: {search_url}")

        try:
            page.goto(search_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # Scroll to load more listings
            for _ in range(3 if not self.test_mode else 1):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Huurstunt listing URLs follow pattern:
            # /appartement/huren/in/amsterdam/STREET/ID
            # /kamer/huren/in/amsterdam/STREET/ID
            for link in soup.select("a"):
                href = link.get("href", "")
                # Match listing URLs: /TYPE/huren/in/amsterdam/STREET/ID
                if re.match(r"^/(appartement|kamer|studio|woning)/huren/in/amsterdam/[^/]+/[a-zA-Z0-9]+$", href):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            console.print(f"  Found {len(urls)} listing links")

        except Exception as e:
            console.print(f"  [red]Error: {e}[/]")

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Huurstunt listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Title
        title_el = soup.select_one("h1, .property-title, .listing-title")
        if title_el:
            data["title"] = title_el.get_text(strip=True)

        # Price - look for euro amounts
        price_patterns = [".price", ".rent-price", '[class*="price"]', ".listing-price"]
        for pattern in price_patterns:
            for el in soup.select(pattern):
                price_text = el.get_text(strip=True)
                # Match patterns like €1.500 or €1500 or 1500
                price_match = re.search(r"€?\s*([\d.]+)", price_text)
                if price_match:
                    price_str = price_match.group(1).replace(".", "")
                    try:
                        price = float(price_str)
                        if 500 <= price <= 10000:  # Sanity check for monthly rent
                            data["price_eur"] = price
                            break
                    except ValueError:
                        continue
            if "price_eur" in data:
                break

        # Address
        address_el = soup.select_one(".address, .location, .property-location")
        if address_el:
            data["address"] = address_el.get_text(strip=True)

        # Extract from full page text
        full_text = soup.get_text()

        # Surface area
        surface_match = re.search(r"(\d+)\s*m[²2]", full_text)
        if surface_match:
            data["surface_m2"] = float(surface_match.group(1))

        # Rooms
        rooms_match = re.search(r"(\d+)\s*(?:kamer|room|slaapkamer)", full_text, re.IGNORECASE)
        if rooms_match:
            data["rooms"] = int(rooms_match.group(1))

        # Furnished
        text_lower = full_text.lower()
        if "gemeubileerd" in text_lower or "furnished" in text_lower:
            if "ongemeubileerd" in text_lower or "unfurnished" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"
        elif "gestoffeerd" in text_lower:
            data["furnished"] = "Upholstered"

        # Description
        desc_el = soup.select_one(".description, .property-description, .content")
        if desc_el:
            data["description"] = desc_el.get_text(strip=True)[:2000]

        # Features from list items
        for li in soup.select("li, .feature, .spec"):
            li_text = li.get_text(strip=True).lower()

            if "slaapkamer" in li_text or "bedroom" in li_text:
                match = re.search(r"(\d+)", li_text)
                if match:
                    data["bedrooms"] = int(match.group(1))

            if "badkamer" in li_text or "bathroom" in li_text:
                match = re.search(r"(\d+)", li_text)
                if match:
                    data["bathrooms"] = int(match.group(1))

            if "energie" in li_text or "energy" in li_text:
                label_match = re.search(r"[A-G]\+*", li_text.upper())
                if label_match:
                    data["energy_label"] = label_match.group()

        # Postal code
        postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
        if postal_match:
            data["postal_code"] = postal_match.group(1).replace(" ", "")

        return data
