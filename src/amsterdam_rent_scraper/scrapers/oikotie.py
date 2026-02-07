"""Oikotie.fi scraper - largest Finnish housing site (AngularJS, JavaScript rendered)."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class OikotieScraper(PlaywrightBaseScraper):
    """Scraper for oikotie.fi Finnish rental listings.

    Oikotie Asunnot is Finland's largest housing marketplace.
    The site uses AngularJS and requires JavaScript rendering.
    Listings are loaded dynamically via XHR after initial page load.

    URL patterns:
    - Search: https://asunnot.oikotie.fi/vuokra-asunnot/helsinki?pagination=1
    - Listing: https://asunnot.oikotie.fi/vuokra-asunnot/helsinki/{id}
    """

    site_name = "oikotie"
    base_url = "https://asunnot.oikotie.fi"

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
        # Block images only (keep scripts/CSS for Angular rendering)
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Helsinki area rentals."""
        # Search in greater Helsinki area
        base = f"{self.base_url}/vuokra-asunnot"
        params = []

        # Price filter if set
        if self.min_price:
            params.append(f"price%5Bmin%5D={self.min_price}")
        if self.max_price:
            params.append(f"price%5Bmax%5D={self.max_price}")

        # Add locations - Helsinki, Espoo, Vantaa
        # Oikotie uses encoded location parameters
        params.append("locations=%5B%5B1656,4,%22Helsinki%22%5D,%5B1549,4,%22Espoo%22%5D,%5B1643,4,%22Vantaa%22%5D%5D")

        # Pagination
        params.append(f"pagination={page_num}")

        if params:
            return f"{base}?{'&'.join(params)}"
        return base

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs."""
        try:
            # Look for common consent button patterns
            consent_selectors = [
                'button:has-text("Hyväksy kaikki")',
                'button:has-text("Accept all")',
                'button:has-text("Hyväksy")',
                '#onetrust-accept-btn-handler',
                '.accept-cookies',
            ]
            for selector in consent_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        page.wait_for_timeout(1000)
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def _wait_for_listings(self, page: Page, timeout: int = 30000):
        """Wait for listing cards to appear on the page."""
        try:
            # Wait for card container to appear
            page.wait_for_selector(
                'div[class*="cards"], div[class*="listing-card"], .ng-cards-v2',
                timeout=timeout
            )
        except Exception:
            # Fallback - just wait a bit
            page.wait_for_timeout(5000)

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        seen_ids = set()

        search_url = self.get_search_url(page_num=1)
        console.print(f"  Fetching: {search_url}")

        try:
            # Navigate to search page
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            self._handle_cookie_consent(page)

            # Wait for dynamic content to load
            page.wait_for_timeout(5000)
            self._wait_for_listings(page)

            # Determine total pages from pagination
            max_pages = 1
            try:
                # Look for pagination info - pattern "Sivu X / Y" or total pages span
                page_text = page.content()
                total_match = re.search(r'totalPages["\']?\s*[:=]\s*(\d+)', page_text)
                if total_match:
                    max_pages = min(int(total_match.group(1)), 20)  # Cap at 20 pages
                else:
                    # Try finding pagination buttons
                    pagination = page.locator('.pagination__pages button, .pagination a')
                    if pagination.count() > 0:
                        # Get highest page number from pagination buttons
                        for i in range(pagination.count()):
                            try:
                                text = pagination.nth(i).text_content()
                                if text and text.isdigit():
                                    max_pages = max(max_pages, int(text))
                            except Exception:
                                continue
            except Exception as e:
                console.print(f"  [yellow]Could not determine page count: {e}[/]")

            max_pages = min(max_pages, 10)  # Limit to avoid too many requests
            console.print(f"  Scraping up to {max_pages} page(s)")

            # Scrape each page
            for page_num in range(1, max_pages + 1):
                if page_num > 1:
                    page_url = self.get_search_url(page_num=page_num)
                    page.goto(page_url, wait_until="networkidle", timeout=60000)
                    page.wait_for_timeout(3000)
                    self._wait_for_listings(page)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # Find listing links - Oikotie uses numeric IDs in URLs
                # Pattern: /vuokra-asunnot/{area}/{id} or full URL with same pattern
                page_urls = []
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    # Match rental listing URLs with numeric ID (relative or absolute)
                    # Examples:
                    #   /vuokra-asunnot/helsinki/22033724
                    #   https://asunnot.oikotie.fi/vuokra-asunnot/helsinki/22033724
                    listing_match = re.search(r"vuokra-asunnot/[^/]+/(\d{5,})", href)
                    if listing_match:
                        listing_id = listing_match.group(1)
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            # Ensure we have a full URL
                            if href.startswith("http"):
                                page_urls.append(href.split("?")[0])  # Remove query params
                            else:
                                page_urls.append(urljoin(self.base_url, href).split("?")[0])

                console.print(f"  Page {page_num}: found {len(page_urls)} new listings")
                urls.extend(page_urls)

                # Check if we have enough
                if self.max_listings and len(urls) >= self.max_listings:
                    break

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/]")

        console.print(f"  Total: {len(urls)} listing URLs found")
        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse an Oikotie listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Get full text for regex extraction
        full_text = soup.get_text(" ", strip=True)

        # Title from page title or h1
        title_el = soup.select_one("title")
        if title_el:
            title_text = title_el.get_text(strip=True)
            # Clean up "| Oikotie" suffix
            data["title"] = re.sub(r"\s*\|\s*Oikotie.*$", "", title_text)

        if "title" not in data:
            h1 = soup.select_one("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)

        # Overview section - contains key info
        overview = soup.select_one('div[class*="listing-overview"]')
        if overview:
            overview_text = overview.get_text(" ", strip=True)
            data["overview"] = overview_text

        # Extract structured data from definition lists
        # Oikotie uses dt/dd pairs for property details
        for dt in soup.find_all("dt"):
            dt_text = dt.get_text(strip=True).lower()
            dd = dt.find_next_sibling("dd")
            if not dd:
                continue
            dd_text = dd.get_text(strip=True)

            # Map Finnish field names to our schema
            field_mappings = {
                "vuokra": "price_raw",
                "vuokra/kk": "price_raw",
                "rent": "price_raw",
                "pinta-ala": "surface_raw",
                "asuinpinta-ala": "surface_raw",
                "living area": "surface_raw",
                "huoneita": "rooms_raw",
                "huoneet": "rooms_raw",
                "rooms": "rooms_raw",
                "huoneistoselite": "room_description",
                "kerros": "floor",
                "floor": "floor",
                "rakennusvuosi": "year_built_raw",
                "year built": "year_built_raw",
                "vapautuu": "available_from",
                "available": "available_from",
                "sijainti": "address_raw",
                "osoite": "address_raw",
                "address": "address_raw",
                "kaupunginosa": "neighborhood",
                "district": "neighborhood",
                "energialuokka": "energy_label",
                "energy class": "energy_label",
                "taloyhtiö": "building_name",
                "building": "building_name",
            }

            for fi_key, our_key in field_mappings.items():
                if fi_key in dt_text:
                    data[our_key] = dd_text
                    break

        # Parse price from raw value
        if "price_raw" in data:
            price_match = re.search(r"(\d[\d\s]*)\s*€", data["price_raw"])
            if price_match:
                price_str = price_match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 100 <= price <= 10000:
                        data["price_eur"] = price
                except ValueError:
                    pass

        # Alternative price extraction from full text
        if "price_eur" not in data:
            price_patterns = [
                r"(\d[\d\s]*)\s*€\s*/\s*(?:kk|kuukausi|month)",
                r"vuokra[:\s]*(\d[\d\s]*)\s*€",
                r"rent[:\s]*(\d[\d\s]*)\s*€",
            ]
            for pattern in price_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                    try:
                        price = float(price_str)
                        if 100 <= price <= 10000:
                            data["price_eur"] = price
                            break
                    except ValueError:
                        continue

        # Parse surface area
        if "surface_raw" in data:
            surface_match = re.search(r"(\d+(?:[.,]\d+)?)", data["surface_raw"])
            if surface_match:
                try:
                    data["surface_m2"] = float(surface_match.group(1).replace(",", "."))
                except ValueError:
                    pass

        if "surface_m2" not in data:
            surface_match = re.search(r"(\d+(?:[.,]\d+)?)\s*m[²2]", full_text)
            if surface_match:
                try:
                    data["surface_m2"] = float(surface_match.group(1).replace(",", "."))
                except ValueError:
                    pass

        # Parse rooms - Finnish format: "2h+k" = 2 rooms + kitchen
        if "rooms_raw" in data or "room_description" in data:
            room_text = data.get("rooms_raw", "") or data.get("room_description", "")
            room_match = re.search(r"(\d+)\s*h", room_text, re.IGNORECASE)
            if room_match:
                data["rooms"] = int(room_match.group(1))

        if "rooms" not in data:
            room_patterns = [
                r"(\d+)\s*h\s*\+",  # 2h+k
                r"(\d+)\s*huone",  # 2 huonetta
            ]
            for pattern in room_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    data["rooms"] = int(match.group(1))
                    break

        # Parse year built
        if "year_built_raw" in data:
            year_match = re.search(r"(\d{4})", data["year_built_raw"])
            if year_match:
                year = int(year_match.group(1))
                if 1800 <= year <= 2030:
                    data["year_built"] = year

        # Address extraction
        if "address_raw" in data:
            data["address"] = data["address_raw"]

        # Try extracting from URL or page content if not found
        if "address" not in data:
            # Check og:title or similar meta tags
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                # Often contains address-like info
                data["address"] = og_title["content"].split("|")[0].strip()

        # Finnish postal code (5 digits)
        postal_match = re.search(r"\b(\d{5})\b", full_text)
        if postal_match:
            postal = postal_match.group(1)
            # Helsinki metro area codes: 00xxx Helsinki, 01xxx Vantaa, 02xxx Espoo
            if postal[:2] in ("00", "01", "02"):
                data["postal_code"] = postal

        # Energy label
        if "energy_label" not in data:
            energy_match = re.search(r"energia(?:luokka)?[:\s]*([A-G])\b", full_text, re.IGNORECASE)
            if energy_match:
                data["energy_label"] = energy_match.group(1).upper()

        # Sauna - very common in Finnish apartments
        if re.search(r"\bsauna\b", full_text, re.IGNORECASE):
            data["has_sauna"] = True

        # Balcony
        if re.search(r"\b(parveke|balcony)\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True

        # Description from meta or specific element
        desc_el = soup.select_one('meta[name="description"]')
        if desc_el and desc_el.get("content"):
            data["description"] = desc_el["content"][:2000]

        # Fallback description from overview
        if "description" not in data and "overview" in data:
            data["description"] = data["overview"][:2000]

        # Property type - Oikotie mainly has apartments
        data["property_type"] = "Apartment"

        # Clean up temporary fields
        for key in ["price_raw", "surface_raw", "rooms_raw", "year_built_raw", "address_raw", "room_description", "overview"]:
            data.pop(key, None)

        return data
