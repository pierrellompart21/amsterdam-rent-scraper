"""Avara scraper - Finnish rental company with JSON API."""

import httpx
from rich.console import Console

from amsterdam_rent_scraper.scrapers.base import BaseScraper, create_scraping_progress

console = Console()


class AvaraScraper(BaseScraper):
    """Scraper for avara.fi Finnish rental listings.

    Avara is a Finnish property company with ~7,000 rental apartments.
    Their site has a public JSON API that returns apartment listings.

    Features:
    - Public JSON API at oma.avara.fi/api/apartments/free
    - Supports location, price filtering
    - Returns all data needed: price, area, rooms, address, coordinates
    - No JS rendering required
    """

    site_name = "avara"
    base_url = "https://www.avara.fi"
    api_url = "https://oma.avara.fi/api/apartments/free"

    # Helsinki metropolitan area locations (case-insensitive set for filtering)
    HELSINKI_METRO_CITIES = {"helsinki", "espoo", "vantaa", "kauniainen"}

    def get_listing_urls(self) -> list[str]:
        """Get listing URLs from the Avara API.

        Avara returns all data from the API, so we generate listing page URLs
        for reference but actually parse the API data directly.
        """
        return self._fetch_listings_from_api()

    def _fetch_listings_from_api(self) -> list[str]:
        """Fetch listings from Avara's JSON API."""
        urls = []

        # Fetch all apartments and filter for Helsinki metro area
        # The API doesn't handle multiple cities well with comma-separated values,
        # so we fetch all and filter client-side
        params = {
            "maxRent": self.max_price,
            "offset": 0,
            "pageSize": 300,  # Get all apartments
            "timezone": "helsinki",  # Required by API
            "locations": "",  # Empty = get all
        }

        try:
            console.print("  Fetching from Avara API (all locations)")
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9,fi;q=0.8",
            }

            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(self.api_url, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            apartments = data.get("consumerApartments", [])
            total = data.get("totalListItemCount", 0)
            console.print(f"  API returned {len(apartments)} apartments (total: {total})")

            # Filter for Helsinki metro area and price range
            filtered = []
            for apt in apartments:
                city = apt.get("city", "").lower()
                rent = apt.get("rentEur", 0)

                # Must be in Helsinki metro area
                if city not in self.HELSINKI_METRO_CITIES:
                    continue

                # Must meet price minimum
                if not rent or rent < self.min_price:
                    continue

                filtered.append(apt)

            console.print(f"  After filtering (Helsinki metro, >={self.min_price}): {len(filtered)} apartments")

            # Store apartment data for later parsing
            self._cached_apartments = {}
            for apt in filtered:
                apt_id = apt.get("id")
                if apt_id:
                    self._cached_apartments[apt_id] = apt
                    # Generate a listing URL (even though we have all the data)
                    # The actual apartment pages are at /en/rental-apartments/[city]/[id]
                    city = apt.get("city", "helsinki").lower()
                    url = f"{self.base_url}/en/rental-apartments/{city}/{apt_id}"
                    urls.append(url)

        except Exception as e:
            console.print(f"  [red]Error fetching from API: {e}[/]")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/]")

        return urls

    def scrape_all(self) -> list[dict]:
        """Full scrape pipeline using cached API data.

        Override base scrape_all to use cached API data instead of
        fetching individual pages.
        """
        console.print(f"[bold cyan]Scraping {self.site_name}...[/]")

        urls = self.get_listing_urls()

        # Apply max_listings limit if set
        if self.max_listings is not None:
            urls = urls[: self.max_listings]
            console.print(f"  Found {len(urls)} listing URLs (limit: {self.max_listings})")
        else:
            console.print(f"  Found {len(urls)} listing URLs (no limit)")

        if not urls:
            console.print(f"[yellow]{self.site_name}: no listings found[/]")
            return []

        results = []
        failed = 0

        with create_scraping_progress() as progress:
            task = progress.add_task(f"{self.site_name}", total=len(urls))

            for url in urls:
                try:
                    # Extract apartment ID from URL
                    apt_id = self._extract_id_from_url(url)

                    if hasattr(self, '_cached_apartments') and apt_id in self._cached_apartments:
                        apt_data = self._cached_apartments[apt_id]
                        data = self._parse_api_apartment(apt_data)
                        data["listing_url"] = url
                        data["raw_page_path"] = ""  # No raw page since we use API
                        data["source_site"] = self.site_name
                        results.append(data)
                    else:
                        failed += 1
                        console.print(f"  [yellow]No cached data for {url}[/]")
                except Exception as e:
                    failed += 1
                    console.print(f"  [red]Failed ({url[:50]}...): {e}[/]")
                finally:
                    progress.advance(task)

        status = "[green]" if failed == 0 else "[yellow]"
        console.print(
            f"{status}{self.site_name}: scraped {len(results)} listings"
            + (f" ({failed} failed)" if failed else "")
            + "[/]"
        )
        return results

    def _extract_id_from_url(self, url: str) -> str | None:
        """Extract apartment ID from URL like /rental-apartments/helsinki/uuid."""
        import re
        # Avara uses UUID format for apartment IDs
        match = re.search(r"/rental-apartments/[^/]+/([a-f0-9-]+)", url)
        if match:
            return match.group(1)
        return None

    def _parse_api_apartment(self, apt: dict) -> dict:
        """Parse an apartment object from the Avara API."""
        data = {}

        # Address and location
        address = apt.get("locationAddress", "")
        city = apt.get("city", "")
        district = apt.get("district", "")

        if address:
            data["title"] = address
            if district and city:
                data["address"] = f"{address}, {district}, {city}"
            elif city:
                data["address"] = f"{address}, {city}"
            else:
                data["address"] = address

        if district:
            data["neighborhood"] = district

        # Price (monthly rent)
        rent = apt.get("rentEur")
        if rent and isinstance(rent, (int, float)):
            data["price_eur"] = float(rent)

        # Surface area
        area = apt.get("areaSqm")
        if area and isinstance(area, (int, float)):
            data["surface_m2"] = float(area)

        # Rooms
        rooms = apt.get("roomCount")
        if rooms and isinstance(rooms, int):
            data["rooms"] = rooms

        # Layout (e.g., "2h+kk")
        layout = apt.get("layout", "")
        if layout and "description" not in data:
            data["description"] = f"Layout: {layout}"

        # Coordinates
        lat = apt.get("latitude")
        lng = apt.get("longitude")
        if lat and lng:
            data["latitude"] = float(lat)
            data["longitude"] = float(lng)

        # Availability date
        available = apt.get("availableDate")
        if available:
            data["available_from"] = available

        # Special status flags
        if apt.get("isAra"):
            data["is_subsidized"] = True
            desc = data.get("description", "")
            if desc:
                data["description"] = f"{desc}. ARA-subsidized housing."
            else:
                data["description"] = "ARA-subsidized housing."

        # Realty name (building/complex name)
        realty = apt.get("realtyName")
        if realty:
            desc = data.get("description", "")
            if desc:
                data["description"] = f"{desc} ({realty})"
            else:
                data["description"] = realty

        # Property type
        data["property_type"] = "Apartment"

        return data

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a listing page HTML.

        This is a fallback method required by BaseScraper.
        Since we use the API, this is rarely called.
        """
        # For Avara, we get all data from the API, so this is just a fallback
        return {
            "title": "Avara Apartment",
            "property_type": "Apartment",
        }
