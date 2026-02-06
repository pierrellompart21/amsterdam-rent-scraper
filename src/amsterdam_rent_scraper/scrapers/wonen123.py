"""123wonen.nl scraper - Dutch rental agency with good HTML structure."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from amsterdam_rent_scraper.scrapers.base import BaseScraper, console


class Wonen123Scraper(BaseScraper):
    """Scraper for 123wonen.nl rental listings."""

    site_name = "123wonen"
    base_url = "https://www.123wonen.nl"

    def get_search_url(self, page: int = 1) -> str:
        """Build search URL for given page."""
        base = f"{self.base_url}/huurwoningen/in/amsterdam"
        params = f"?minprice={self.min_price}&maxprice={self.max_price}"
        if page > 1:
            params += f"&page={page}"
        return base + params

    def get_listing_urls(self) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page = 1
        max_pages = 2 if self.test_mode else 50

        while page <= max_pages:
            search_url = self.get_search_url(page)
            console.print(f"  Fetching search page {page}: {search_url}")

            try:
                html = self.fetch_page(search_url)
                soup = BeautifulSoup(html, "lxml")

                listing_links_found = []

                # Find links to listing pages - pattern: /huur/amsterdam/*/
                for link in soup.select("a[href*='/huur/amsterdam/']"):
                    href = link.get("href", "")
                    # Listing URLs have pattern /huur/amsterdam/type/address-id-14
                    if re.search(r"/huur/amsterdam/[^/]+/[^/]+-\d+-14", href):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in listing_links_found:
                            listing_links_found.append(full_url)

                # Alternative: also try /huur/[city]/[type]/[slug] pattern
                if not listing_links_found:
                    for link in soup.select("a[href*='/huur/']"):
                        href = link.get("href", "")
                        if re.search(r"/huur/[^/]+/[^/]+/[^/]+", href):
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
                next_link = soup.select_one('a[href*="page=' + str(page + 1) + '"]')
                if not next_link:
                    # Also check for "volgende" (next) button
                    next_link = soup.select_one('a.volgende, a[rel="next"]')
                if not next_link:
                    break

                page += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page}: {e}[/]")
                break

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Try JSON-LD structured data first
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                json_data = json.loads(script.string)
                items = json_data if isinstance(json_data, list) else [json_data]
                for item in items:
                    item_type = item.get("@type", "")
                    if item_type in ("Residence", "House", "Apartment", "Product"):
                        if "name" in item:
                            data["title"] = item["name"]
                        if "description" in item:
                            data["description"] = item["description"][:2000]
                        if "address" in item:
                            addr = item["address"]
                            if isinstance(addr, str):
                                data["address"] = addr
                            elif isinstance(addr, dict):
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
                        # Coordinates
                        if "geo" in item:
                            geo = item["geo"]
                            if isinstance(geo, dict):
                                if "latitude" in geo:
                                    data["latitude"] = float(geo["latitude"])
                                if "longitude" in geo:
                                    data["longitude"] = float(geo["longitude"])
                        break
            except (json.JSONDecodeError, TypeError):
                continue

        text = soup.get_text(separator=" ")

        # HTML fallback for title
        if "title" not in data:
            title_el = soup.select_one("h1")
            if title_el:
                data["title"] = title_el.get_text(strip=True)

        # Price - look for "€X.XXX,-" or "€X.XXX"
        if "price_eur" not in data:
            price_match = re.search(r"€\s*([\d.]+)(?:,-)?(?:\s*(?:per|/|p\.m\.|p/m))?", text)
            if price_match:
                price_str = price_match.group(1).replace(".", "")
                try:
                    data["price_eur"] = float(price_str)
                except ValueError:
                    pass

        # Surface area - "XX m²" or "Woonoppervlakte XX m²"
        if "surface_m2" not in data:
            surface_match = re.search(r"(?:Woonoppervlakte|oppervlakte)?\s*(\d+)\s*m[²2]", text, re.I)
            if surface_match:
                data["surface_m2"] = float(surface_match.group(1))

        # Rooms - "X kamers" or "Kamers X"
        if "rooms" not in data:
            rooms_match = re.search(r"(?:(\d+)\s*kamers|Kamers\s*(\d+))", text, re.I)
            if rooms_match:
                data["rooms"] = int(rooms_match.group(1) or rooms_match.group(2))

        # Bedrooms - "X slaapkamers" or "Slaapkamers X"
        if "bedrooms" not in data:
            bed_match = re.search(r"(?:(\d+)\s*slaapkamer|Slaapkamer[s]?\s*(\d+))", text, re.I)
            if bed_match:
                data["bedrooms"] = int(bed_match.group(1) or bed_match.group(2))

        # Energy label
        energy_match = re.search(r"(?:Energielabel|energie)\s*([A-G]\+*)", text, re.I)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Furnished status - Dutch: gemeubileerd/gestoffeerd/kaal
        if re.search(r"gemeubileerd", text, re.I):
            data["furnished"] = "Furnished"
        elif re.search(r"gestoffeerd", text, re.I):
            data["furnished"] = "Upholstered"
        elif re.search(r"kaal|ongemeubileerd", text, re.I):
            data["furnished"] = "Unfurnished"

        # Available date - "Per direct" or date
        if re.search(r"per\s*direct|direct\s*beschikbaar", text, re.I):
            data["available_date"] = "Immediately"
        else:
            avail_match = re.search(
                r"(?:beschikbaar|available)[^\d]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
                text,
                re.I,
            )
            if avail_match:
                data["available_date"] = avail_match.group(1)

        # Deposit
        deposit_match = re.search(r"(?:borg|waarborgsom|deposit)\s*€?\s*([\d.]+)", text, re.I)
        if deposit_match:
            dep_str = deposit_match.group(1).replace(".", "")
            try:
                data["deposit_eur"] = float(dep_str)
            except ValueError:
                pass

        # Service costs
        service_match = re.search(r"servicekosten\s*€?\s*([\d.]+)", text, re.I)
        if service_match:
            svc_str = service_match.group(1).replace(".", "")
            try:
                data["service_costs_eur"] = float(svc_str)
            except ValueError:
                pass

        # Address from text if not found in JSON-LD
        if "address" not in data:
            # Try to find postal code pattern
            postal_match = re.search(r"(\d{4}\s?[A-Z]{2})\s*(Amsterdam|Amstelveen|Diemen)", text)
            if postal_match:
                data["postal_code"] = postal_match.group(1).replace(" ", "")
                data["address"] = f"{postal_match.group(1)} {postal_match.group(2)}"

        # Agency
        if "123wonen" in text.lower():
            agency_match = re.search(r"(123\s*Wonen\s*[A-Za-z]+)", text, re.I)
            if agency_match:
                data["agency"] = agency_match.group(1)
            else:
                data["agency"] = "123Wonen"

        return data
