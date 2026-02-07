"""Retta Management scraper - Finnish rental company with Next.js site."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class RettaScraper(PlaywrightBaseScraper):
    """Scraper for vuokraus.rettamanagement.fi Finnish rental listings.

    Retta Management is a Finnish property management company.
    Their site is Next.js-based and embeds all listing data in __NEXT_DATA__.

    Features:
    - All listings available in JSON via __NEXT_DATA__
    - ~1600 apartments across Finland
    - Filter for Helsinki metro area (Helsinki, Espoo, Vantaa, Kauniainen)
    - Data includes: address, price, area, rooms, features
    """

    site_name = "retta"
    base_url = "https://vuokraus.rettamanagement.fi"

    # Helsinki metropolitan area cities (case-insensitive matching)
    HELSINKI_METRO_CITIES = {"helsinki", "espoo", "vantaa", "kauniainen"}

    # Feature translations (Finnish -> English)
    FEATURE_MAP = {
        "parveke": "balcony",
        "sauna": "sauna",
        "hissi": "elevator",
        "varasto": "storage",
        "vaatehuone": "walk-in closet",
        "lemmikit_sallittu": "pets allowed",
        "savuton": "smoke-free",
        "astianpesukone": "dishwasher",
        "esteeton": "accessible",
        "uudiskohde": "new construction",
    }

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
        # Block images only (keep scripts/CSS for Next.js)
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self) -> str:
        """Return the apartments listing URL."""
        return f"{self.base_url}/asunnot"

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs if present."""
        try:
            consent_selectors = [
                'button:has-text("Hyväksy kaikki")',
                'button:has-text("Hyväksy")',
                'button:has-text("Accept all")',
                'button:has-text("Accept")',
                '#onetrust-accept-btn-handler',
            ]
            for selector in consent_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        page.wait_for_timeout(1500)
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def _is_helsinki_area(self, city: str) -> bool:
        """Check if a city is in the Helsinki metropolitan area."""
        return city.lower() in self.HELSINKI_METRO_CITIES

    def _extract_listings_from_next_data(self, html: str) -> list[dict]:
        """Extract listing data from __NEXT_DATA__ JSON."""
        soup = BeautifulSoup(html, "lxml")
        script = soup.select_one('script#__NEXT_DATA__')

        if not script:
            console.print("  [yellow]Could not find __NEXT_DATA__ script[/]")
            return []

        try:
            data = json.loads(script.string)
            items = data.get("props", {}).get("pageProps", {}).get("items", [])
            return items
        except (json.JSONDecodeError, TypeError) as e:
            console.print(f"  [red]Error parsing __NEXT_DATA__: {e}[/]")
            return []

    def get_listing_urls(self, page: Page) -> list[str]:
        """Get listing URLs for Helsinki area apartments.

        For Retta, we extract data directly from __NEXT_DATA__ which contains
        all listings. We filter for Helsinki metro area and return URLs.
        """
        urls = []

        search_url = self.get_search_url()
        console.print(f"  Fetching: {search_url}")

        try:
            # Navigate to apartments page
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            self._handle_cookie_consent(page)
            page.wait_for_timeout(2000)

            # Extract data from __NEXT_DATA__
            html = page.content()
            all_items = self._extract_listings_from_next_data(html)

            console.print(f"  Found {len(all_items)} total listings in __NEXT_DATA__")

            # Filter for Helsinki metro area
            helsinki_items = []
            for item in all_items:
                city_district = item.get("cityDistrict", {})
                city = city_district.get("city", "")
                if self._is_helsinki_area(city):
                    helsinki_items.append(item)

            console.print(f"  Found {len(helsinki_items)} Helsinki area listings")

            # Store items in instance for later parsing (avoid re-fetching)
            self._cached_items = {item.get("id"): item for item in helsinki_items}

            # Generate URLs
            for item in helsinki_items:
                href = item.get("href", "")
                if href:
                    full_url = urljoin(self.base_url, href)
                    urls.append(full_url)

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/]")

        return urls[: self.max_listings] if self.max_listings else urls

    def scrape_all(self) -> list[dict]:
        """Full scrape pipeline using cached data from __NEXT_DATA__.

        Override base scrape_all to avoid fetching individual pages
        since all data is available from the search page.
        """
        from amsterdam_rent_scraper.scrapers.playwright_base import create_scraping_progress

        console.print(f"[bold cyan]Scraping {self.site_name} (Playwright)...[/]")

        try:
            page = self._new_page()
            urls = self.get_listing_urls(page)
            page.close()

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
                        # Use cached data instead of fetching individual pages
                        listing_id = self._extract_id_from_url(url)
                        if hasattr(self, '_cached_items') and listing_id in self._cached_items:
                            cached_item = self._cached_items[listing_id]
                            data = self._parse_cached_item(cached_item, url)
                            data["listing_url"] = url
                            data["raw_page_path"] = ""  # No raw page since we use cached data
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
            console.print(f"{status}{self.site_name}: scraped {len(results)} listings" + (f" ({failed} failed)" if failed else "") + "[/]")
            return results
        finally:
            self._close_browser()

    def _extract_id_from_url(self, url: str) -> int | None:
        """Extract listing ID from URL like /asunnot/17430."""
        match = re.search(r"/asunnot/(\d+)", url)
        if match:
            return int(match.group(1))
        return None

    def _parse_cached_item(self, item: dict, url: str) -> dict:
        """Parse a cached listing item from __NEXT_DATA__."""
        data = {}

        # Title (address)
        data["title"] = item.get("title", "")

        # Address and location
        city_district = item.get("cityDistrict", {})
        city = city_district.get("city", "")
        district = city_district.get("district", "")

        if city and district:
            data["address"] = f"{item.get('title', '')}, {district}, {city}"
            data["neighborhood"] = district
        elif item.get("subtitle"):
            data["address"] = item["subtitle"]

        # Price
        price = item.get("price")
        if price and isinstance(price, (int, float)):
            data["price_eur"] = float(price)

        # Surface area
        area = item.get("area")
        if area and isinstance(area, (int, float)):
            data["surface_m2"] = float(area)

        # Rooms
        rooms = item.get("rooms")
        if rooms and isinstance(rooms, int):
            data["rooms"] = rooms

        # Features
        features = item.get("features", [])
        if "hissi" in features:
            data["has_elevator"] = True
        if "sauna" in features:
            data["has_sauna"] = True
        if "parveke" in features:
            data["has_balcony"] = True

        # Availability
        if item.get("tagRight"):
            tag = item["tagRight"]
            # "Vapautumassa 01.03.26" or "Heti vapaa"
            if "heti" in tag.lower():
                data["available_from"] = "Heti vapaa"
            else:
                # Try to extract date
                date_match = re.search(r"(\d{2}\.\d{2}\.\d{2,4})", tag)
                if date_match:
                    data["available_from"] = date_match.group(1)

        # Campaign/promo
        if item.get("campaign"):
            data["description"] = item["campaign"][:500]

        # Details text (e.g., "3h, kt, lasitettu parveke")
        details = item.get("details", "")
        if details and "description" not in data:
            data["description"] = details

        # Property type
        data["property_type"] = "Apartment"

        return data

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Retta listing page and extract data.

        This is a fallback for when cached data isn't available.
        """
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # First try to get data from __NEXT_DATA__
        script = soup.select_one('script#__NEXT_DATA__')
        if script:
            try:
                json_data = json.loads(script.string)
                page_props = json_data.get("props", {}).get("pageProps", {})
                apartment = page_props.get("apartment", {})

                if apartment:
                    # Title/address
                    data["title"] = apartment.get("title", "")

                    # Address components
                    city = apartment.get("city", "")
                    district = apartment.get("district", "")
                    if city and district:
                        data["address"] = f"{apartment.get('address', '')}, {district}, {city}"
                        data["neighborhood"] = district

                    # Price
                    if apartment.get("rent"):
                        data["price_eur"] = float(apartment["rent"])

                    # Area
                    if apartment.get("area"):
                        data["surface_m2"] = float(apartment["area"])

                    # Rooms
                    if apartment.get("rooms"):
                        data["rooms"] = int(apartment["rooms"])

                    # Features
                    features = apartment.get("features", [])
                    if "hissi" in features:
                        data["has_elevator"] = True
                    if "sauna" in features:
                        data["has_sauna"] = True
                    if "parveke" in features:
                        data["has_balcony"] = True

                    # Description
                    if apartment.get("description"):
                        data["description"] = apartment["description"][:2000]

                    data["property_type"] = "Apartment"

                    return data
            except (json.JSONDecodeError, TypeError, KeyError):
                pass

        # Fallback: parse from HTML
        full_text = soup.get_text(" ", strip=True)

        # Title
        h1 = soup.select_one("h1")
        if h1:
            data["title"] = h1.get_text(strip=True)

        # Price
        price_patterns = [
            r"(\d[\d\s]*)\s*€\s*/\s*(?:kk|kuukausi)",
            r"vuokra[:\s]*(\d[\d\s]*)\s*€",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 300 <= price <= 5000:
                        data["price_eur"] = price
                        break
                except ValueError:
                    continue

        # Surface area
        surface_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m[²2]", full_text)
        if surface_match:
            try:
                data["surface_m2"] = float(surface_match.group(1).replace(",", "."))
            except ValueError:
                pass

        # Rooms
        room_match = re.search(r"(\d+)\s*[Hh]\s*\+", full_text)
        if room_match:
            try:
                data["rooms"] = int(room_match.group(1))
            except ValueError:
                pass

        # Elevator
        if re.search(r"\bhissi\b", full_text, re.IGNORECASE):
            data["has_elevator"] = True

        # Sauna
        if re.search(r"\bsauna\b", full_text, re.IGNORECASE):
            data["has_sauna"] = True

        # Balcony
        if re.search(r"\bparveke\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True

        data["property_type"] = "Apartment"

        return data
