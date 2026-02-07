"""TA.fi scraper - TA-Asunnot rental company (server-rendered HTML)."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class TAScraper(PlaywrightBaseScraper):
    """Scraper for ta.fi Finnish rental listings.

    TA-Asunnot has over 5,000 rental apartments in Finland.
    The site is WordPress-based with server-rendered HTML.
    URL pattern: /asunnot/etsi-asuntoa/{id}-{address}-{district}-{city}-{type}-{id}/
    """

    site_name = "ta"
    base_url = "https://ta.fi"

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
        # Block images only (keep scripts for any JS that might load content)
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self) -> str:
        """Return the search URL for Helsinki rentals."""
        return f"{self.base_url}/asunnot/vuokra-asunto/helsinki/"

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        seen_ids = set()

        search_url = self.get_search_url()
        console.print(f"  Fetching: {search_url}")

        try:
            # Navigate to search page
            page.goto(search_url, wait_until="networkidle", timeout=60000)

            # Handle any cookie consent if present
            try:
                consent_selectors = [
                    'button:has-text("Hyväksy kaikki")',
                    'button:has-text("Accept all")',
                    '#onetrust-accept-btn-handler',
                ]
                for selector in consent_selectors:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        page.wait_for_timeout(2000)
                        break
            except Exception:
                pass

            # Wait for content
            page.wait_for_timeout(3000)

            # TA.fi uses "Load more" pagination - click until we have enough
            max_clicks = 10 if not self.test_mode else 1
            for _ in range(max_clicks):
                # Try to find and click "Lataa lisää" (Load more)
                try:
                    load_more = page.locator('button:has-text("Lataa lisää")')
                    if load_more.count() > 0 and load_more.first.is_visible():
                        load_more.first.click()
                        page.wait_for_timeout(2000)
                    else:
                        break
                except Exception:
                    break

                # Check if we have enough listings
                html = page.content()
                soup = BeautifulSoup(html, "lxml")
                current_count = len(
                    [
                        a
                        for a in soup.find_all("a", href=True)
                        if "/asunnot/etsi-asuntoa/" in a.get("href", "")
                        and "vuokra" in a.get("href", "").lower()
                    ]
                )
                if self.max_listings and current_count >= self.max_listings:
                    break

            # Extract final HTML
            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Find apartment links
            # Pattern: /asunnot/etsi-asuntoa/{id}-{address}-{district}-{city}-vuokra-{id}/
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "/asunnot/etsi-asuntoa/" in href and "vuokra" in href.lower():
                    # Skip general search pages
                    if href.endswith("/etsi-asuntoa/") or "?" in href:
                        continue

                    # Extract unique ID from URL (first number)
                    id_match = re.search(r"/(\d+)-", href)
                    if id_match:
                        listing_id = id_match.group(1)
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            full_url = urljoin(self.base_url, href)
                            urls.append(full_url)

            console.print(f"  Found {len(urls)} Helsinki rental listings")

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")
            import traceback

            console.print(f"  [dim]{traceback.format_exc()}[/]")

        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a TA.fi listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Get full text for regex extraction
        full_text = soup.get_text(" ", strip=True)

        # Try to extract data from the Findkit JSON (embedded search data)
        for script in soup.select("script#findkit"):
            try:
                json_text = script.string
                if json_text:
                    # Parse the escaped JSON
                    findkit_data = json.loads(json_text.replace("&quot;", '"'))
                    custom_fields = findkit_data.get("customFields", {})

                    # Area (size in m²)
                    if custom_fields.get("area", {}).get("value"):
                        area_str = custom_fields["area"]["value"]
                        try:
                            data["surface_m2"] = float(area_str.replace(",", "."))
                        except (ValueError, TypeError):
                            pass

                    # Apartment type (e.g., "2h+kt")
                    if custom_fields.get("apartmentType", {}).get("value"):
                        apt_type = custom_fields["apartmentType"]["value"]
                        # Extract room count
                        room_match = re.search(r"(\d+)h", apt_type, re.IGNORECASE)
                        if room_match:
                            data["rooms"] = int(room_match.group(1))

                    # Postal code
                    if custom_fields.get("postNumber", {}).get("value"):
                        data["postal_code"] = custom_fields["postNumber"]["value"]

                    # Quarter (district)
                    if custom_fields.get("quarter", {}).get("value"):
                        data["neighborhood"] = custom_fields["quarter"]["value"]

                    # Title
                    if findkit_data.get("title"):
                        data["title"] = findkit_data["title"]
            except (json.JSONDecodeError, TypeError, AttributeError):
                continue

        # Title from h1 or meta
        if "title" not in data:
            h1 = soup.select_one("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)

        if "title" not in data:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Price - "X €/kk" format in SinglePage__SubTitle
        price_el = soup.select_one(".SinglePage__SubTitle")
        if price_el:
            price_text = price_el.get_text(strip=True)
            price_match = re.search(r"([\d\s,\.]+)\s*€", price_text)
            if price_match:
                price_str = (
                    price_match.group(1)
                    .replace(" ", "")
                    .replace("\u00a0", "")
                    .replace(",", ".")
                )
                try:
                    price = float(price_str)
                    if 100 <= price <= 5000:
                        data["price_eur"] = price
                except ValueError:
                    pass

        # Fallback price from text
        if "price_eur" not in data:
            price_patterns = [
                r"([\d\s,\.]+)\s*€\s*/\s*(?:kk|kuukausi)",
                r"vuokra[:\s]*([\d\s,\.]+)\s*€",
            ]
            for pattern in price_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    price_str = (
                        match.group(1)
                        .replace(" ", "")
                        .replace("\u00a0", "")
                        .replace(",", ".")
                    )
                    try:
                        price = float(price_str)
                        if 100 <= price <= 5000:
                            data["price_eur"] = price
                            break
                    except ValueError:
                        continue

        # Surface area fallback
        if "surface_m2" not in data:
            surface_patterns = [
                r"(\d+(?:[.,]\d+)?)\s*m[²2]",
                r"pinta-ala[:\s]*(\d+(?:[.,]\d+)?)",
            ]
            for pattern in surface_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    surface_str = match.group(1).replace(",", ".")
                    try:
                        surface = float(surface_str)
                        if 10 <= surface <= 500:
                            data["surface_m2"] = surface
                            break
                    except ValueError:
                        continue

        # Rooms fallback
        if "rooms" not in data:
            room_patterns = [
                r"(\d+)\s*h\s*\+",  # 2h+k
                r"(\d+)\s*huone",  # 2 huonetta
            ]
            for pattern in room_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    try:
                        data["rooms"] = int(match.group(1))
                        break
                    except ValueError:
                        continue

        # Extract address from URL
        # Pattern: /asunnot/etsi-asuntoa/{id}-{street}-{district}-{city}-vuokra-{id}/
        url_match = re.search(
            r"/asunnot/etsi-asuntoa/\d+-([^/]+)-vuokra-\d+", url, re.IGNORECASE
        )
        if url_match:
            address_parts = url_match.group(1).split("-")
            # Filter out city and district names we might have
            if len(address_parts) >= 3:
                # Reconstruct address - typically: street-apt-district-subdistrict-city
                street_parts = []
                for part in address_parts:
                    if part.lower() in ("helsinki", "espoo", "vantaa"):
                        break
                    street_parts.append(part.replace("-", " ").title())
                if street_parts:
                    data["address"] = " ".join(street_parts[:3])  # First 3 parts usually enough

        # Floor
        floor_patterns = [
            r"(\d+)\s*/\s*\d+\s*(?:kerros|krs)",  # 2/5 kerros
            r"(\d+)[\.\s]*kerros",  # 2. kerros
            r"kerros[:\s]*(\d+)",  # kerros: 2
        ]
        for pattern in floor_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["floor"] = match.group(1)
                break

        # Postal code fallback
        if "postal_code" not in data:
            postal_match = re.search(r"\b(\d{5})\b", full_text)
            if postal_match:
                postal = postal_match.group(1)
                # Helsinki metro area codes start with 00, 01, 02
                if postal[:2] in ("00", "01", "02"):
                    data["postal_code"] = postal

        # Elevator (hissi)
        if "hissi" in full_text.lower() or "additional-hope-hissi" in html:
            data["has_elevator"] = True

        # Sauna
        if "sauna" in full_text.lower():
            data["has_sauna"] = True

        # Balcony (parveke)
        if "parveke" in full_text.lower() or "additional-hope-parveke" in html:
            data["has_balcony"] = True

        # Availability
        avail_patterns = [
            r"vapautuu[:\s]*(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
            r"(heti\s*vapaa)",
        ]
        for pattern in avail_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["available_from"] = match.group(1).strip()
                break

        # Check status from HTML classes
        if "status-vacant" in html or "heti-vapaa" in html:
            data["available_from"] = "Heti vapaa"

        # Description from page content
        desc_el = soup.select_one(".text-wrap")
        if desc_el:
            data["description"] = desc_el.get_text(strip=True)[:2000]

        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        # Property type - TA.fi mainly has apartments
        data["property_type"] = "Apartment"

        # Energy label
        energy_match = re.search(
            r"energia(?:luokka)?[:\s]*([A-G])\b", full_text, re.IGNORECASE
        )
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Year built
        year_match = re.search(
            r"(?:rakennus|valmistumis)?vuosi[:\s]*(\d{4})", full_text, re.IGNORECASE
        )
        if year_match:
            data["year_built"] = int(year_match.group(1))

        return data
