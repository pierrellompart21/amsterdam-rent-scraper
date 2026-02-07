"""OVV Asuntopalvelut scraper - Auroranlinna rental apartments in Helsinki."""

import json
import re

from playwright.sync_api import Page, Response

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class OVVScraper(PlaywrightBaseScraper):
    """Scraper for ovv.com Finnish rental listings.

    OVV Asuntopalvelut manages rentals for Auroranlinna (City of Helsinki) and others.
    They have ~6,000 apartments in Helsinki. The site uses WordPress with AJAX to load
    listings, so we intercept the JSON API response.

    Features:
    - WordPress with AJAX for dynamic listing loading
    - Intercepts JSON response from ovv_plugin_get_realties endpoint
    - Filters for Helsinki Auroranlinna office
    """

    site_name = "ovv"
    base_url = "https://www.ovv.com"

    # Helsinki metropolitan area cities
    HELSINKI_METRO_CITIES = {"helsinki", "espoo", "vantaa", "kauniainen"}

    def _new_page(self) -> Page:
        """Create a new page with Finnish locale settings."""
        browser = self._get_browser()
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="fi-FI",
        )
        page = context.new_page()
        # Block images to speed up
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self) -> str:
        """Return the search URL for Helsinki rentals."""
        # Use "Helsinki" office filter to get Helsinki city listings
        return f"{self.base_url}/en/for-rent/?cities=Helsinki"

    def _is_helsinki_area(self, address: str) -> bool:
        """Check if address is in Helsinki metro area."""
        addr_lower = address.lower()
        return any(city in addr_lower for city in self.HELSINKI_METRO_CITIES)

    def get_listing_urls(self, page: Page) -> list[str]:
        """Return listing URLs - but we use a different approach (API interception)."""
        # OVV site uses AJAX, so we return empty here and handle in scrape_all
        return []

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a listing page - not used since we get data from JSON API."""
        return {}

    def _parse_json_listing(self, realty: dict) -> dict:
        """Parse a single listing from the OVV JSON API response."""
        data = {}

        # Address
        address = realty.get("address", "")
        if address:
            data["address"] = address
            # Extract neighborhood from address (e.g., "Puolikuu 2 B 3, 02210 Espoo, Olari")
            parts = address.split(", ")
            if len(parts) >= 3:
                data["neighborhood"] = parts[-1]  # Last part is usually district

        # Title - use address if no separate title
        data["title"] = address if address else "OVV Rental"

        # Postal code from dedicated field or address
        postcode = realty.get("postcode")
        if postcode:
            data["postal_code"] = str(postcode)
        else:
            for part in address.split(", "):
                postal_match = re.search(r"\b(\d{5})\b", part)
                if postal_match:
                    data["postal_code"] = postal_match.group(1)
                    break

        # City detail (neighborhood)
        city_detail = realty.get("city_detail")
        if city_detail and "neighborhood" not in data:
            data["neighborhood"] = city_detail

        # Price from default_rate_amount
        rent = realty.get("default_rate_amount")
        if rent is not None:
            try:
                rent_val = float(rent)
                if 100 <= rent_val <= 5000:
                    data["price_eur"] = rent_val
            except (ValueError, TypeError):
                pass

        # Surface area from apartment_area
        size = realty.get("apartment_area")
        if size is not None:
            try:
                data["surface_m2"] = float(size)
            except (ValueError, TypeError):
                pass

        # Room count - try multiple sources
        rooms = realty.get("no_of_rooms")
        if rooms is not None:
            try:
                data["rooms"] = int(rooms)
            except (ValueError, TypeError):
                pass

        # Fallback to type info
        if "rooms" not in data:
            apt_type = realty.get("type", {})
            if apt_type:
                type_rooms = apt_type.get("no_of_rooms")
                if type_rooms is not None:
                    try:
                        data["rooms"] = int(type_rooms)
                    except (ValueError, TypeError):
                        pass
                type_name = apt_type.get("name", "")
                if type_name and "rooms" not in data:
                    parsed_rooms = self._parse_finnish_room_count(type_name)
                    if parsed_rooms:
                        data["rooms"] = parsed_rooms

        # Floor from level_no
        floor = realty.get("level_no")
        if floor is not None:
            try:
                data["floor"] = int(floor)
            except (ValueError, TypeError):
                pass

        # Building type
        building_type = realty.get("building_type", {})
        if building_type:
            bt_name = building_type.get("name", "")
            if "kerrostalo" in bt_name.lower():
                data["property_type"] = "Apartment"
            elif "rivitalo" in bt_name.lower():
                data["property_type"] = "Row House"
            elif "paritalo" in bt_name.lower():
                data["property_type"] = "Semi-detached"
            else:
                data["property_type"] = "Apartment"

        # Balcony
        balcony = realty.get("balcony", {})
        if balcony and balcony.get("name"):
            data["has_balcony"] = True

        # Sauna
        sauna = realty.get("sauna")
        if sauna:
            data["has_sauna"] = True

        # Elevator (hissi)
        elevator = realty.get("elevator")
        if elevator:
            data["has_elevator"] = True

        # Year built from year_of_constructions
        year_built = realty.get("year_of_constructions")
        if year_built:
            try:
                data["year_built"] = int(year_built)
            except (ValueError, TypeError):
                pass

        # Energy class
        energy_class = realty.get("energy_class")
        if energy_class:
            data["energy_label"] = str(energy_class).upper()

        # Availability
        available = realty.get("available_date")
        if available:
            data["available_from"] = available
        elif realty.get("available_now"):
            data["available_from"] = "Heti vapaa"

        # Listing URL
        listing_id = realty.get("id")
        if listing_id:
            data["listing_url"] = f"{self.base_url}/en/for-rent/realty/{listing_id}/"

        # Kitchen type for description
        kitchen = realty.get("kitchen_type", {})
        condition = realty.get("condition", {})
        desc_parts = []
        if kitchen and kitchen.get("name"):
            desc_parts.append(f"Kitchen: {kitchen['name']}")
        if condition and condition.get("name"):
            desc_parts.append(f"Condition: {condition['name']}")
        if desc_parts:
            data["description"] = ". ".join(desc_parts)

        return data

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

    def scrape_all(self) -> list[dict]:
        """Scrape OVV by intercepting the AJAX API response."""
        console.print(f"[bold cyan]Scraping {self.site_name} (Playwright + API)...[/]")

        results = []
        captured_json = []

        try:
            page = self._new_page()

            # Set up response interceptor
            def handle_response(response: Response):
                if "admin-ajax" in response.url:
                    try:
                        body = response.text()
                        if body.startswith("{") and "realties" in body:
                            captured_json.append(body)
                    except Exception:
                        pass

            page.on("response", handle_response)

            search_url = self.get_search_url()
            console.print(f"  Fetching: {search_url}")

            # Navigate and let AJAX load
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(5000)

            page.close()

            # Process captured JSON
            if captured_json:
                console.print(f"  Captured {len(captured_json)} API response(s)")
                for json_str in captured_json:
                    try:
                        data = json.loads(json_str)
                        realties = data.get("realties", [])
                        console.print(f"  Found {len(realties)} listings in response")

                        for realty in realties:
                            # Filter for Helsinki metro area
                            address = realty.get("address", "")
                            if not self._is_helsinki_area(address):
                                continue

                            parsed = self._parse_json_listing(realty)
                            if parsed:
                                parsed["source_site"] = self.site_name
                                parsed["raw_page_path"] = ""  # No raw HTML for API data
                                results.append(parsed)

                            # Check max listings limit
                            if self.max_listings and len(results) >= self.max_listings:
                                break

                    except json.JSONDecodeError as e:
                        console.print(f"  [yellow]JSON parse error: {e}[/]")

                    if self.max_listings and len(results) >= self.max_listings:
                        break
            else:
                console.print("  [yellow]No API responses captured[/]")

            console.print(f"[green]{self.site_name}: scraped {len(results)} listings[/]")
            return results

        except Exception as e:
            console.print(f"  [red]Error: {e}[/]")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/]")
            return []

        finally:
            self._close_browser()
