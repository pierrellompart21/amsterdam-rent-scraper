"""Keva scraper - Finnish pension fund rental apartments."""

import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from rich.console import Console

from amsterdam_rent_scraper.scrapers.base import BaseScraper, create_scraping_progress

console = Console()


class KevaScraper(BaseScraper):
    """Scraper for vuokra-asunnot.keva.fi Finnish rental listings.

    Keva is Finland's largest pension provider and owns ~3,500 rental apartments.
    Their site is WordPress-based with server-rendered HTML, no JavaScript required.

    Features:
    - Server-rendered HTML (no JS required)
    - Clean HTML structure with apartments listed on homepage
    - Individual apartment pages with full details
    - Filters for Helsinki metro area (Helsinki, Espoo, Vantaa)
    """

    site_name = "keva"
    base_url = "https://vuokra-asunnot.keva.fi"

    # Helsinki metropolitan area cities (case-insensitive matching)
    HELSINKI_METRO_CITIES = {"helsinki", "espoo", "vantaa", "kauniainen"}

    def _is_helsinki_area(self, location_text: str) -> bool:
        """Check if location is in Helsinki metro area."""
        location_lower = location_text.lower()
        return any(city in location_lower for city in self.HELSINKI_METRO_CITIES)

    def _parse_finnish_room_count(self, room_text: str) -> int | None:
        """Parse Finnish room notation like 'kaksio' or '3h+k' to room count."""
        room_lower = room_text.lower()

        # Finnish room type words
        room_words = {
            "yksiö": 1,
            "kaksio": 2,
            "kolmio": 3,
            "neliö": 4,
            "viisiö": 5,
        }
        for word, count in room_words.items():
            if word in room_lower:
                return count

        # Pattern like "2h+k" or "3h+kk"
        match = re.search(r"(\d+)\s*h", room_lower)
        if match:
            return int(match.group(1))

        return None

    def get_listing_urls(self) -> list[str]:
        """Get apartment listing URLs from Keva homepage.

        The homepage displays all available apartments in a grid.
        We extract URLs and filter for Helsinki metro area.
        """
        urls = []

        try:
            console.print(f"  Fetching: {self.base_url}")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,fi;q=0.8",
            }

            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(self.base_url, headers=headers)
                resp.raise_for_status()
                html = resp.text

            soup = BeautifulSoup(html, "lxml")

            # Find all apartment cards with class "item--main-search"
            apartment_cards = soup.select("li.item--main-search article")

            console.print(f"  Found {len(apartment_cards)} apartment cards on homepage")

            # Also cache some basic info from the cards for faster parsing
            self._cached_card_data = {}

            for card in apartment_cards:
                # Get listing URL
                link = card.select_one("a[href*='/asunto/']")
                if not link:
                    continue

                href = link.get("href", "")
                if not href:
                    continue

                # Get location (city, district)
                header = card.select_one(".item__post__header")
                if header:
                    # Location is typically in a <p> tag like "Helsinki Pikku-Huopalahti"
                    location_p = header.select_one("p")
                    location = location_p.get_text(strip=True) if location_p else ""

                    # Filter for Helsinki metro area
                    if not self._is_helsinki_area(location):
                        continue

                # Get basic info from card (for caching)
                summary = card.select_one(".entry-summary")
                card_data = {"location": location}

                if summary:
                    # Extract layout and price/size from summary
                    # Format: "2h+k+lasitettuparveke" and "56m², 1140 €/kk"
                    paragraphs = summary.select("p")
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        card_data["summary_text"] = card_data.get("summary_text", "") + " " + text

                # Full URL
                full_url = urljoin(self.base_url, href.rstrip("/"))
                urls.append(full_url)
                self._cached_card_data[full_url] = card_data

            console.print(f"  After filtering (Helsinki metro area): {len(urls)} apartments")

        except Exception as e:
            console.print(f"  [red]Error fetching listings: {e}[/]")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/]")

        return urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Keva apartment page and extract details.

        The page has structured data in labeled <p> and <table> elements.
        """
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Title from <title> tag or h1
        title_tag = soup.select_one("title")
        if title_tag:
            # Format: "Tilkankuja 6 B 11 - KEVA"
            title = title_tag.get_text(strip=True)
            if " - " in title:
                data["title"] = title.split(" - ")[0].strip()

        # Try to get full text for pattern matching
        full_text = soup.get_text(" ", strip=True)

        # Address - look for "Osoite" label
        address_patterns = [
            (r"Osoite[:\s]+([^,\n]+(?:\s+\d+\s*[A-Za-z]?\s*\d*))", "pattern"),
        ]

        # Look for structured info in <p><strong> format
        info_paragraphs = soup.select("p")
        for p in info_paragraphs:
            text = p.get_text(" ", strip=True)

            # Address
            if "Osoite" in text:
                match = re.search(r"Osoite[:\s]*(.+?)(?:$|\n)", text)
                if match:
                    data["address"] = match.group(1).strip()

            # Price - "Vuokra: 1140 €/kk"
            if "Vuokra:" in text:
                match = re.search(r"(\d[\d\s]*)\s*€", text)
                if match:
                    price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                    try:
                        price = float(price_str)
                        if 300 <= price <= 5000:
                            data["price_eur"] = price
                    except ValueError:
                        pass

            # Surface area - "Pinta-ala: 56 m²"
            if "Pinta-ala" in text:
                match = re.search(r"(\d+(?:[.,]\d+)?)\s*m", text)
                if match:
                    try:
                        data["surface_m2"] = float(match.group(1).replace(",", "."))
                    except ValueError:
                        pass

            # Room count - "Huoneiden lukumäärä: kaksio" or layout like "2h+k"
            if "Huoneiden" in text or "Huoneistotyyppi" in text:
                rooms = self._parse_finnish_room_count(text)
                if rooms:
                    data["rooms"] = rooms

            # Pets allowed
            if "Lemmikit sallittu" in text and "kyllä" in text.lower():
                data["pets_allowed"] = True

            # Floor
            if "Kerros" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    data["floor"] = int(match.group(1))

        # Also try table format (detailed info table)
        table_rows = soup.select("tr")
        for row in table_rows:
            header = row.select_one("th")
            value = row.select_one("td")
            if header and value:
                header_text = header.get_text(strip=True)
                value_text = value.get_text(strip=True)

                if "Osoite" in header_text and "address" not in data:
                    data["address"] = value_text

                if "Vuokra" in header_text and "price_eur" not in data:
                    match = re.search(r"(\d[\d\s]*)\s*€", value_text)
                    if match:
                        price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                        try:
                            data["price_eur"] = float(price_str)
                        except ValueError:
                            pass

                if "Pinta-ala" in header_text and "surface_m2" not in data:
                    match = re.search(r"(\d+(?:[.,]\d+)?)", value_text)
                    if match:
                        try:
                            data["surface_m2"] = float(match.group(1).replace(",", "."))
                        except ValueError:
                            pass

        # Location/neighborhood from cached card data or breadcrumb
        if hasattr(self, "_cached_card_data") and url in self._cached_card_data:
            cached = self._cached_card_data[url]
            if cached.get("location"):
                # Location like "Helsinki Pikku-Huopalahti"
                parts = cached["location"].split()
                if len(parts) >= 2:
                    data["neighborhood"] = parts[1]
                    # Add city to address if not present
                    if "address" in data and parts[0].lower() in self.HELSINKI_METRO_CITIES:
                        if parts[0] not in data["address"]:
                            data["address"] = f"{data['address']}, {cached['location']}"

        # Extract neighborhood from breadcrumb if not found
        breadcrumb = soup.select_one(".breadcrumb-row")
        if breadcrumb and "neighborhood" not in data:
            # Breadcrumb has links to building/location
            breadcrumb_text = breadcrumb.get_text(" ", strip=True)
            # Look for district name in breadcrumb
            for city in self.HELSINKI_METRO_CITIES:
                if city in breadcrumb_text.lower():
                    # Try to find district after city name
                    match = re.search(rf"{city}[_\s](\w+)", breadcrumb_text, re.IGNORECASE)
                    if match:
                        data["neighborhood"] = match.group(1)
                        break

        # Description from og:description meta tag
        og_desc = soup.select_one('meta[property="og:description"]')
        if og_desc:
            desc = og_desc.get("content", "")
            if desc:
                data["description"] = desc[:1000]

        # Elevator - check for "hissi" but watch for negations
        # "ei hissiä" means no elevator, "hissi" alone means has elevator
        if re.search(r"\bei\s+hissi", full_text, re.IGNORECASE):
            data["has_elevator"] = False
        elif re.search(r"\bhissi\b", full_text, re.IGNORECASE):
            data["has_elevator"] = True

        # Sauna
        if re.search(r"\bsauna\b", full_text, re.IGNORECASE):
            data["has_sauna"] = True

        # Balcony
        if re.search(r"\bparveke\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True

        # Property type - kerrostalo = apartment building
        if re.search(r"\bkerrostalo\b", full_text, re.IGNORECASE):
            data["property_type"] = "Apartment"
        elif re.search(r"\brivitalo\b", full_text, re.IGNORECASE):
            data["property_type"] = "Row House"
        else:
            data["property_type"] = "Apartment"

        return data
