"""DirectWonen.nl scraper - requires JavaScript for listings to load."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class DirectWonenScraper(PlaywrightBaseScraper):
    """Scraper for directwonen.nl rental listings (JavaScript required)."""

    site_name = "directwonen"
    base_url = "https://directwonen.nl"

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Amsterdam rentals."""
        # DirectWonen URL structure: /huurwoningen-huren/amsterdam?pageno=N
        url = f"{self.base_url}/huurwoningen-huren/amsterdam"
        if page_num > 1:
            url += f"?pageno={page_num}"
        return url

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page_num = 1
        max_pages = 2 if self.test_mode else 20

        while page_num <= max_pages:
            search_url = self.get_search_url(page_num)
            console.print(f"  Fetching search page {page_num}: {search_url}")

            try:
                page.goto(search_url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(2000)

                # Scroll to trigger lazy loading
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # DirectWonen listing links follow pattern:
                # /huurwoningen-huren/amsterdam/STREET/TYPE-ID
                page_urls = []
                for link in soup.select("a"):
                    href = link.get("href", "")
                    # Match listing URLs with ID suffix like appartement-509529
                    if "/huurwoningen-huren/amsterdam/" in href:
                        # Must have property type + ID pattern
                        if re.search(r"/(appartement|studio|kamer|woning)-\d+", href):
                            full_url = urljoin(self.base_url, href)
                            if full_url not in urls and full_url not in page_urls:
                                page_urls.append(full_url)

                if not page_urls:
                    console.print(f"  No listings found on page {page_num}")
                    break

                urls.extend(page_urls)
                console.print(f"  Page {page_num}: found {len(page_urls)} links")

                # Check for next page
                next_page_link = soup.select_one(f'a[href*="pageno={page_num + 1}"]')
                if not next_page_link:
                    break

                page_num += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page_num}: {e}[/]")
                break

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a DirectWonen listing page and extract data.

        Note: DirectWonen hides most details (price, m², rooms) behind a paywall.
        We extract what we can from the URL and visible elements.
        """
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Property type from URL (e.g., /appartement-509529)
        type_match = re.search(r"/(appartement|studio|kamer|woning)-\d+", url)
        if type_match:
            type_mapping = {
                "appartement": "Apartment",
                "studio": "Studio",
                "kamer": "Room",
                "woning": "House",
            }
            data["property_type"] = type_mapping.get(type_match.group(1), type_match.group(1).title())

        # Title from URL - extract street name
        # URL pattern: /huurwoningen-huren/amsterdam/STREET/TYPE-ID
        url_match = re.search(r"/huurwoningen-huren/amsterdam/([^/]+)/(\w+)-\d+", url)
        if url_match:
            street = url_match.group(1).replace("-", " ").title()
            prop_type = url_match.group(2).replace("-", " ").title()
            data["title"] = f"{prop_type} - {street}, Amsterdam"
            data["address"] = f"{street}, Amsterdam"

        # Title - try multiple selectors (but these are often generic on DirectWonen)
        if "title" not in data:
            for selector in ["h1", ".property-title", ".listing-title"]:
                title_el = soup.select_one(selector)
                if title_el:
                    title_text = title_el.get_text(strip=True)
                    # Skip generic titles like "Smart Only" or subscription-related
                    if title_text and "smart" not in title_text.lower() and len(title_text) > 5:
                        data["title"] = title_text
                        break

        # Price - DirectWonen requires login to see actual rental prices
        # The visible prices are subscription prices (€10.95, €19.95, €34.95)
        # We don't extract price here to avoid misinterpreting subscription prices as rent
        # Price will remain None and get filtered out by the pipeline's price filter

        # Address
        address_patterns = [".address", ".location", ".property-address", '[class*="address"]']
        for pattern in address_patterns:
            address_el = soup.select_one(pattern)
            if address_el:
                data["address"] = address_el.get_text(strip=True)
                break

        # Look for structured data in page
        text = soup.get_text().lower()

        # Surface area
        surface_match = re.search(r"(\d+)\s*m[²2]", soup.get_text())
        if surface_match:
            data["surface_m2"] = float(surface_match.group(1))

        # Rooms/bedrooms
        rooms_match = re.search(r"(\d+)\s*(?:kamer|room|slaapkamer|bedroom)", soup.get_text(), re.IGNORECASE)
        if rooms_match:
            data["rooms"] = int(rooms_match.group(1))

        # Furnished status
        if "gemeubileerd" in text or "furnished" in text:
            if "ongemeubileerd" in text or "unfurnished" in text:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"

        # Description
        desc_patterns = [".description", ".property-description", ".listing-description", '[class*="description"]']
        for pattern in desc_patterns:
            desc_el = soup.select_one(pattern)
            if desc_el:
                data["description"] = desc_el.get_text(strip=True)[:2000]
                break

        # Try to extract from feature lists/tables
        feature_items = soup.select("li, .feature, .property-feature, dd")
        for item in feature_items:
            item_text = item.get_text(strip=True).lower()

            if "m²" in item_text or "m2" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match and "surface_m2" not in data:
                    data["surface_m2"] = float(match.group(1))

            if "slaapkamer" in item_text or "bedroom" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match:
                    data["bedrooms"] = int(match.group(1))

            if "badkamer" in item_text or "bathroom" in item_text:
                match = re.search(r"(\d+)", item_text)
                if match:
                    data["bathrooms"] = int(match.group(1))

        # Postal code from address or page
        if "address" in data:
            postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", data["address"])
            if postal_match:
                data["postal_code"] = postal_match.group(1).replace(" ", "")

        return data
