"""Huurwoningen.nl scraper - Dutch rental site with good JSON-LD structured data."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from amsterdam_rent_scraper.scrapers.base import BaseScraper, console


class HuurwoningenScraper(BaseScraper):
    """Scraper for huurwoningen.nl rental listings."""

    site_name = "huurwoningen"
    base_url = "https://www.huurwoningen.nl"

    def get_search_url(self, page: int = 1) -> str:
        """Build search URL for given page."""
        base = f"{self.base_url}/in/amsterdam/"
        params = f"?prijs={self.min_price}-{self.max_price}"
        if page > 1:
            params += f"&page={page}"
        return base + params

    def get_listing_urls(self) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page = 1
        max_pages = 2 if self.test_mode else 500  # Safety limit

        while page <= max_pages:
            # Early exit if we have enough listings
            if self.max_listings is not None and len(urls) >= self.max_listings:
                break
            search_url = self.get_search_url(page)
            console.print(f"  Fetching search page {page}: {search_url}")

            try:
                html = self.fetch_page(search_url)
                soup = BeautifulSoup(html, "lxml")

                # Try JSON-LD first for listing URLs
                listing_links_found = []
                for script in soup.select('script[type="application/ld+json"]'):
                    try:
                        data = json.loads(script.string)
                        # Handle both single object and array
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if item.get("@type") == "ItemList":
                                for elem in item.get("itemListElement", []):
                                    url = elem.get("url")
                                    if url:
                                        listing_links_found.append(url)
                    except (json.JSONDecodeError, TypeError):
                        continue

                # Fallback: find links to listing pages
                if not listing_links_found:
                    for link in soup.select("a[href*='/huren/amsterdam/']"):
                        href = link.get("href", "")
                        # Listing URLs have pattern /huren/amsterdam/{uuid}/{street}/
                        if re.search(r"/huren/amsterdam/[a-f0-9]+/", href):
                            full_url = urljoin(self.base_url, href)
                            if full_url not in listing_links_found:
                                listing_links_found.append(full_url)

                if not listing_links_found:
                    console.print(f"  No listings found on page {page}")
                    break

                for url in listing_links_found:
                    if url not in urls:
                        urls.append(url)

                console.print(f"  Page {page}: found {len(listing_links_found)} links")

                # Check for next page
                next_link = soup.select_one(f'a[href*="page={page + 1}"]')
                if not next_link:
                    break

                page += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page}: {e}[/]")
                break

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a listing page and extract data using JSON-LD or HTML fallback."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Try JSON-LD structured data first (most reliable)
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                json_data = json.loads(script.string)
                items = json_data if isinstance(json_data, list) else [json_data]
                for item in items:
                    item_types = item.get("@type", [])
                    if not isinstance(item_types, list):
                        item_types = [item_types]

                    if "House" in item_types or "Apartment" in item_types or "Product" in item_types:
                        # Extract from JSON-LD
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

                        # Rooms
                        rooms = item.get("numberOfRooms")
                        if isinstance(rooms, dict):
                            rooms = rooms.get("value")
                        if rooms:
                            try:
                                data["rooms"] = int(rooms)
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

                        # Price from offers
                        offers = item.get("offers", {})
                        if isinstance(offers, dict):
                            price = offers.get("price")
                            if price:
                                try:
                                    data["price_eur"] = float(price)
                                except (ValueError, TypeError):
                                    pass

                        break  # Found our main item
            except (json.JSONDecodeError, TypeError):
                continue

        # HTML fallback for missing fields
        if "title" not in data:
            title_el = soup.select_one("h1")
            if title_el:
                data["title"] = title_el.get_text(strip=True)

        if "price_eur" not in data:
            # Look for price pattern like "€ 1.500 per maand"
            price_match = re.search(r"€\s*([\d.,]+)\s*(?:per|/)", soup.get_text())
            if price_match:
                price_str = price_match.group(1).replace(".", "").replace(",", ".")
                try:
                    data["price_eur"] = float(price_str)
                except ValueError:
                    pass

        if "surface_m2" not in data:
            # Look for surface pattern like "85 m²"
            surface_match = re.search(r"(\d+)\s*m[²2]", soup.get_text())
            if surface_match:
                data["surface_m2"] = float(surface_match.group(1))

        if "rooms" not in data:
            # Look for rooms pattern like "3 kamers" or "3 rooms"
            rooms_match = re.search(r"(\d+)\s*(?:kamer|room)", soup.get_text(), re.I)
            if rooms_match:
                data["rooms"] = int(rooms_match.group(1))

        # Try to get additional details from page text
        text = soup.get_text(separator=" ")

        # Energy label
        energy_match = re.search(r"(?:energie|energy)[^\w]*([A-G]\+*)", text, re.I)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Furnished status
        if re.search(r"(?:gemeubileerd|furnished)", text, re.I):
            data["furnished"] = "Furnished"
        elif re.search(r"(?:gestoffeerd|upholstered)", text, re.I):
            data["furnished"] = "Upholstered"
        elif re.search(r"(?:kaal|unfurnished|ongemeubileerd)", text, re.I):
            data["furnished"] = "Unfurnished"

        # Available date
        avail_match = re.search(
            r"(?:beschikbaar|available)[^\d]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2})",
            text,
            re.I,
        )
        if avail_match:
            data["available_date"] = avail_match.group(1)

        return data
