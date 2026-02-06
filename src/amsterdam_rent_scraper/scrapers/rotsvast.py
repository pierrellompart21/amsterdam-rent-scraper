"""Rotsvast.nl scraper - Dutch rental agency with permissive robots.txt."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from amsterdam_rent_scraper.scrapers.base import BaseScraper, console


class RotsvastScraper(BaseScraper):
    """Scraper for rotsvast.nl rental listings."""

    site_name = "rotsvast"
    base_url = "https://www.rotsvast.nl"

    def get_search_url(self, page: int = 1) -> str:
        """Build search URL for Amsterdam rentals with price filter."""
        # Rotsvast URL structure: /huren/amsterdam/ or /huren/page/N/
        # Filter params available but we'll filter Amsterdam in post-processing
        # since the location filter is by branch office, not city
        if page == 1:
            return f"{self.base_url}/huren/amsterdam/"
        return f"{self.base_url}/huren/amsterdam/page/{page}/"

    def get_listing_urls(self) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page = 1
        max_pages = 2 if self.test_mode else 100  # Safety limit

        while page <= max_pages:
            # Early exit if we have enough listings
            if self.max_listings is not None and len(urls) >= self.max_listings:
                break

            search_url = self.get_search_url(page)
            console.print(f"  Fetching search page {page}: {search_url}")

            try:
                html = self.fetch_page(search_url)
                soup = BeautifulSoup(html, "lxml")

                # Find listing links - Rotsvast uses cards with links to /huren/STREET-CITY-hID/
                page_urls = []
                for link in soup.select('a[href*="/huren/"]'):
                    href = link.get("href", "")
                    # Match pattern: /huren/street-city-hNNNNNN/
                    if re.search(r"/huren/[a-z\-]+-h\d+/?$", href, re.IGNORECASE):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls and full_url not in page_urls:
                            page_urls.append(full_url)

                if not page_urls:
                    console.print(f"  No more listings found on page {page}")
                    break

                urls.extend(page_urls)
                console.print(f"  Page {page}: found {len(page_urls)} links")

                # Check for next page - look for pagination links
                next_link = soup.select_one(f'a[href*="/page/{page + 1}/"]')
                if not next_link:
                    # Also check for "next" button
                    next_link = soup.select_one('a[rel="next"]') or soup.select_one(
                        'a.pagination__next'
                    )
                if not next_link:
                    break

                page += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page}: {e}[/]")
                break

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Rotsvast listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}
        full_text = soup.get_text(" ", strip=True)

        # Title from h1 or meta title
        title_el = soup.select_one("h1")
        if title_el:
            data["title"] = title_el.get_text(strip=True)
        else:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Extract address from title or URL
        # URL pattern: /huren/street-city-hNNNN/
        url_match = re.search(r"/huren/([a-z\-]+)-h\d+/?$", url, re.IGNORECASE)
        if url_match:
            addr_part = url_match.group(1).replace("-", " ").title()
            data["address"] = addr_part

        # Price - look for € pattern
        price_patterns = [
            r"€\s*([\d.,]+)\s*(?:p\.?m\.?|per\s*maand|per\s*month)?",
            r"huurprijs[:\s]*€?\s*([\d.,]+)",
            r"([\d.,]+)\s*(?:euro|€)\s*(?:p\.?m\.?|per\s*maand)?",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(".", "").replace(",", ".")
                price_str = price_str.rstrip(".")
                try:
                    price = float(price_str)
                    if 100 <= price <= 15000:
                        data["price_eur"] = price
                        break
                except ValueError:
                    continue

        # Surface area
        surface_patterns = [
            r"(\d+)\s*m[²2]",
            r"oppervlakte[:\s]*(\d+)",
            r"woonoppervlakte[:\s]*(\d+)",
        ]
        for pattern in surface_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["surface_m2"] = float(match.group(1))
                break

        # Rooms
        room_patterns = [
            r"(\d+)\s*kamer(?:s)?",
            r"kamers[:\s]*(\d+)",
            r"(\d+)\s*room(?:s)?",
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["rooms"] = int(match.group(1))
                break

        # Bedrooms
        bedroom_patterns = [
            r"(\d+)\s*slaapkamer(?:s)?",
            r"slaapkamers[:\s]*(\d+)",
            r"(\d+)\s*bedroom(?:s)?",
        ]
        for pattern in bedroom_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["bedrooms"] = int(match.group(1))
                break

        # Furnished status
        text_lower = full_text.lower()
        if "gemeubileerd" in text_lower:
            data["furnished"] = "Furnished"
        elif "gestoffeerd" in text_lower:
            data["furnished"] = "Upholstered"
        elif "kaal" in text_lower:
            data["furnished"] = "Unfurnished"
        elif "furnished" in text_lower:
            if "unfurnished" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"

        # Property type
        if "appartement" in text_lower or "apartment" in text_lower:
            data["property_type"] = "Apartment"
        elif "woning" in text_lower or "huis" in text_lower or "house" in text_lower:
            data["property_type"] = "House"
        elif "studio" in text_lower:
            data["property_type"] = "Studio"
        elif "kamer" in text_lower and "room" not in data:
            data["property_type"] = "Room"

        # Postal code - Dutch format: 1234AB
        postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
        if postal_match:
            data["postal_code"] = postal_match.group(1).replace(" ", "")

        # Available from
        avail_patterns = [
            r"beschikbaar\s*(?:per|vanaf)?[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"beschikbaar\s*(?:per|vanaf)?[:\s]*(\d{1,2}\s+\w+\s+\d{4})",
            r"available\s*(?:from)?[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"beschikbaar[:\s]*(direct|per direct|immediately)",
        ]
        for pattern in avail_patterns:
            match = re.search(pattern, text_lower)
            if match:
                data["available_from"] = match.group(1)
                break

        # Deposit
        deposit_match = re.search(
            r"(?:borg|waarborgsom|deposit)[:\s]*€?\s*([\d.,]+)",
            text_lower
        )
        if deposit_match:
            deposit_str = deposit_match.group(1).replace(".", "").replace(",", ".")
            try:
                data["deposit_eur"] = float(deposit_str)
            except ValueError:
                pass

        # Energy label
        energy_match = re.search(
            r"(?:energie\s*label|energy\s*label)[:\s]*([A-G]\+*)",
            full_text,
            re.IGNORECASE
        )
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Description - try meta description
        desc_el = soup.select_one('meta[name="description"]')
        if desc_el and desc_el.get("content"):
            data["description"] = desc_el["content"][:2000]
        else:
            # Try to get main content description
            desc_div = soup.select_one(".object-description, .property-description, article")
            if desc_div:
                data["description"] = desc_div.get_text(strip=True)[:2000]

        # Agency - Rotsvast is the agency
        data["agency"] = "Rotsvast"

        return data
