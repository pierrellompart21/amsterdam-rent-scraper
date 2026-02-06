"""Huure.nl scraper - Dutch rental aggregator with server-rendered content."""

import json
import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup

from amsterdam_rent_scraper.scrapers.base import BaseScraper, console


class HuureScraper(BaseScraper):
    """Scraper for huure.nl rental listings."""

    site_name = "huure"
    base_url = "https://huure.nl"

    def get_search_url(self, cursor1: float = None, cursor2: int = None) -> str:
        """Build search URL for Amsterdam apartments."""
        # Huure.nl uses cursor-based pagination
        url = f"{self.base_url}/apartments-for-rent/amsterdam"
        params = {}
        if self.min_price:
            params["min_rent"] = self.min_price
        if self.max_price:
            params["max_rent"] = self.max_price
        if cursor1 is not None and cursor2 is not None:
            params["cursor1"] = cursor1
            params["cursor2"] = cursor2
        if params:
            url += "?" + urlencode(params)
        return url

    def get_listing_urls(self) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page_num = 1
        max_pages = 2 if self.test_mode else 50  # Safety limit
        cursor1 = None
        cursor2 = None

        while page_num <= max_pages:
            # Early exit if we have enough listings
            if self.max_listings is not None and len(urls) >= self.max_listings:
                break

            search_url = self.get_search_url(cursor1, cursor2)
            console.print(f"  Fetching page {page_num}: {search_url[:80]}...")

            try:
                html = self.fetch_page(search_url)
                soup = BeautifulSoup(html, "lxml")

                # Find listing links - pattern: /rental-properties/{description}-{id}
                page_urls = []
                for link in soup.select('a[href*="/rental-properties/"]'):
                    href = link.get("href", "")
                    # Match URLs with numeric ID at the end
                    if re.search(r"/rental-properties/[a-z0-9-]+-\d+$", href):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls and full_url not in page_urls:
                            page_urls.append(full_url)

                if not page_urls:
                    console.print(f"  No listings found on page {page_num}")
                    break

                urls.extend(page_urls)
                console.print(f"  Page {page_num}: found {len(page_urls)} links")

                # Check for "Show more" / next page
                # Huure.nl uses cursor params: ?cursor1=XX&cursor2=YY
                next_link = soup.select_one('a[href*="cursor1="]')
                if next_link:
                    next_href = next_link.get("href", "")
                    # Extract cursor values
                    cursor1_match = re.search(r"cursor1=([\d.]+)", next_href)
                    cursor2_match = re.search(r"cursor2=(\d+)", next_href)
                    if cursor1_match and cursor2_match:
                        cursor1 = float(cursor1_match.group(1))
                        cursor2 = int(cursor2_match.group(1))
                    else:
                        break
                else:
                    # No more pages
                    break

                page_num += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page_num}: {e}[/]")
                break

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Get full text for regex extraction
        full_text = soup.get_text(" ", strip=True)

        # Try JSON-LD structured data first
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    item_type = item.get("@type", "")
                    if item_type in ["Apartment", "House", "Product", "RealEstateListing", "Residence"]:
                        if "name" in item:
                            data["title"] = item["name"]
                        if "description" in item:
                            data["description"] = item["description"][:2000]

                        # Address
                        addr = item.get("address", {})
                        if isinstance(addr, dict):
                            parts = []
                            if addr.get("streetAddress"):
                                parts.append(addr["streetAddress"])
                            if addr.get("postalCode"):
                                data["postal_code"] = addr["postalCode"]
                                parts.append(addr["postalCode"])
                            if addr.get("addressLocality"):
                                parts.append(addr["addressLocality"])
                            if parts:
                                data["address"] = ", ".join(parts)

                        # Price
                        offers = item.get("offers", {})
                        if isinstance(offers, dict) and "price" in offers:
                            try:
                                data["price_eur"] = float(offers["price"])
                            except (ValueError, TypeError):
                                pass

                        # Floor size
                        floor_size = item.get("floorSize")
                        if isinstance(floor_size, dict):
                            floor_size = floor_size.get("value")
                        if floor_size:
                            try:
                                data["surface_m2"] = float(floor_size)
                            except (ValueError, TypeError):
                                pass

                        # Rooms
                        rooms = item.get("numberOfRooms")
                        if isinstance(rooms, dict):
                            rooms = rooms.get("value")
                        if rooms:
                            try:
                                data["rooms"] = int(rooms)
                            except (ValueError, TypeError):
                                pass

                        break
            except (json.JSONDecodeError, TypeError):
                continue

        # Title from H1 or meta
        if "title" not in data:
            h1 = soup.select_one("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)

        if "title" not in data:
            title_el = soup.select_one('meta[property="og:title"]')
            if title_el and title_el.get("content"):
                data["title"] = title_el["content"]

        # Fallback title from URL
        if "title" not in data:
            # URL pattern: /rental-properties/2-room-apartment-in-amsterdam-12341263
            url_match = re.search(r"/rental-properties/([a-z0-9-]+)-\d+$", url)
            if url_match:
                title_from_url = url_match.group(1).replace("-", " ").title()
                data["title"] = title_from_url

        # Price extraction
        if "price_eur" not in data:
            # Pattern: €600 or € 1,500 per month
            price_patterns = [
                r"€\s*([\d.,]+)\s*(?:per month|per maand|p\.?m\.?|/month)?",
                r"rent[:\s]*([\d.,]+)\s*€",
                r"huur[:\s]*€?\s*([\d.,]+)",
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
        if "surface_m2" not in data:
            surface_match = re.search(r"(\d+)\s*m[²2]", full_text)
            if surface_match:
                data["surface_m2"] = float(surface_match.group(1))

        # Rooms
        if "rooms" not in data:
            rooms_match = re.search(r"(\d+)\s*(?:room|kamer)s?\b", full_text, re.IGNORECASE)
            if rooms_match:
                data["rooms"] = int(rooms_match.group(1))

        # Property type from URL or text
        url_lower = url.lower()
        if "apartment" in url_lower or "appartement" in full_text.lower():
            data["property_type"] = "Apartment"
        elif "house" in url_lower or "huis" in full_text.lower():
            data["property_type"] = "House"
        elif "room" in url_lower or "kamer" in full_text.lower():
            data["property_type"] = "Room"
        elif "studio" in url_lower or "studio" in full_text.lower():
            data["property_type"] = "Studio"

        # Address extraction
        if "address" not in data:
            # Dutch street name patterns
            street_patterns = [
                r"([A-Za-z\s]+(?:straat|weg|plein|laan|gracht|kade|singel|dreef|hof|park))",
            ]
            for pattern in street_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    street = match.group(1).strip()
                    if len(street) > 3:
                        data["address"] = street + ", Amsterdam"
                        break

        # Postal code
        if "postal_code" not in data:
            postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
            if postal_match:
                data["postal_code"] = postal_match.group(1).replace(" ", "")

        # Furnished status
        text_lower = full_text.lower()
        if "furnished" in text_lower:
            if "unfurnished" in text_lower or "not furnished" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"
        elif "gemeubileerd" in text_lower:
            data["furnished"] = "Furnished"
        elif "gestoffeerd" in text_lower:
            data["furnished"] = "Upholstered"

        # Available status
        if "available" in text_lower or "beschikbaar" in text_lower:
            avail_patterns = [
                r"available\s*(?:from)?\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
                r"beschikbaar\s*(?:vanaf)?\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
                r"available\s*(?:from)?\s*:?\s*(immediately|now|direct)",
            ]
            for pattern in avail_patterns:
                match = re.search(pattern, text_lower)
                if match:
                    data["available_from"] = match.group(1)
                    break

        # Energy label
        energy_match = re.search(r"energy\s*(?:label)?[:\s]*([A-G]\+*)", full_text, re.IGNORECASE)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Deposit
        deposit_match = re.search(r"deposit[:\s]*€?\s*([\d.,]+)", text_lower)
        if deposit_match:
            deposit_str = deposit_match.group(1).replace(".", "").replace(",", ".")
            try:
                data["deposit_eur"] = float(deposit_str)
            except ValueError:
                pass

        # Description from meta
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        return data
