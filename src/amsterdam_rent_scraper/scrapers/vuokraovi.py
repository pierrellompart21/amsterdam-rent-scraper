"""Vuokraovi.com scraper - major Finnish rental portal (JavaScript rendered)."""

import json
import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class VuokraoviScraper(PlaywrightBaseScraper):
    """Scraper for vuokraovi.com Finnish rental listings.

    Vuokraovi is one of the largest Finnish rental portals.
    The site is React-based and requires JavaScript rendering.
    """

    site_name = "vuokraovi"
    base_url = "https://www.vuokraovi.com"

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
            locale="fi-FI",  # Finnish locale
        )
        page = context.new_page()
        # Block unnecessary resources to speed up
        page.route(
            "**/*.{png,jpg,jpeg,gif,svg,webp,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )
        return page

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Helsinki/Espoo area rentals."""
        # Vuokraovi URL pattern: /vuokra-asunnot/LOCATION
        # We search both Helsinki and Espoo for greater Helsinki area
        # Multiple locations can be specified
        base = f"{self.base_url}/vuokra-asunnot"

        # Build query params
        params = {
            "locale": "en",  # Use English interface
            "pageCount": page_num,
        }

        # Price filtering (vuokra = rent in Finnish)
        if self.min_price:
            params["rentMin"] = self.min_price
        if self.max_price:
            params["rentMax"] = self.max_price

        # Size filtering (only if set in config, which it is for Helsinki)
        # Surface area in m2

        # Location - search Helsinki metropolitan area
        # We'll search without specific location first to get listings
        # The /vuokra-asunnot endpoint shows all rentals
        url = f"{base}?{urlencode(params)}"
        return url

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page_num = 1
        max_pages = 2 if self.test_mode else 20  # Safety limit

        while page_num <= max_pages:
            # Early exit if we have enough listings
            if self.max_listings is not None and len(urls) >= self.max_listings:
                break

            search_url = self.get_search_url(page_num)
            console.print(f"  Fetching search page {page_num}: {search_url[:80]}...")

            try:
                # Navigate with domcontentloaded for React sites
                page.goto(search_url, wait_until="domcontentloaded", timeout=45000)

                # Wait for listing cards to appear
                # Vuokraovi uses Material-UI cards
                try:
                    page.wait_for_selector('a[href*="/vuokra-asunto/"]', timeout=15000)
                except Exception:
                    # Try alternative: look for any clickable listing elements
                    try:
                        page.wait_for_selector('[data-testid="listing-card"]', timeout=5000)
                    except Exception:
                        pass

                # Scroll to load lazy content
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1500)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # Find listing links - vuokra-asunto means rental apartment
                # URL pattern: /vuokra-asunto/LOCATION/TYPE/ID
                page_urls = []
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    # Match rental listing URLs with numeric ID at the end
                    if "/vuokra-asunto/" in href:
                        # Extract and validate URL
                        if re.search(r"/vuokra-asunto/[^/]+/[^/]+/\d+", href):
                            full_url = urljoin(self.base_url, href)
                            if full_url not in urls and full_url not in page_urls:
                                page_urls.append(full_url)

                if not page_urls:
                    console.print(f"  No listings found on page {page_num}")
                    break

                urls.extend(page_urls)
                console.print(f"  Page {page_num}: found {len(page_urls)} links (total: {len(urls)})")

                # Check for next page
                # Look for pagination buttons or "next page" links
                has_next = False
                next_selectors = [
                    f'a[href*="pageCount={page_num + 1}"]',
                    'button[aria-label*="Next"]',
                    'a[aria-label*="Next"]',
                    '[data-testid="pagination-next"]',
                ]
                for selector in next_selectors:
                    if soup.select_one(selector):
                        has_next = True
                        break

                # Also check if there are more pages by seeing if current page < total
                if not has_next:
                    # If we got a full page of results, assume there's more
                    if len(page_urls) >= 20:
                        has_next = True

                if not has_next:
                    break

                page_num += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page_num}: {e}[/]")
                break

        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Vuokraovi listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Get full text for regex extraction
        full_text = soup.get_text(" ", strip=True)

        # Try JSON-LD structured data first (if available)
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    if item.get("@type") in ["Apartment", "House", "RealEstateListing", "Product"]:
                        if "name" in item:
                            data["title"] = item["name"]
                        if "description" in item:
                            data["description"] = item["description"][:2000]
                        if "address" in item:
                            addr = item["address"]
                            if isinstance(addr, dict):
                                parts = []
                                if addr.get("streetAddress"):
                                    parts.append(addr["streetAddress"])
                                if addr.get("addressLocality"):
                                    parts.append(addr["addressLocality"])
                                if addr.get("postalCode"):
                                    data["postal_code"] = addr["postalCode"]
                                if parts:
                                    data["address"] = ", ".join(parts)
            except (json.JSONDecodeError, TypeError):
                continue

        # Title extraction
        if "title" not in data:
            # Try h1 heading
            h1 = soup.select_one("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)

        if "title" not in data:
            # Try og:title
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Price extraction - Finnish format: "1 200 €/kk" (1200 euros per month)
        price_patterns = [
            r"(\d[\d\s]*)\s*€\s*/\s*kk",  # 1 200 €/kk
            r"(\d[\d\s]*)\s*€\s*/\s*(?:kk|kuukausi|month)",  # various monthly formats
            r"vuokra[:\s]*(\d[\d\s]*)\s*€",  # vuokra: 1200 € (rent)
            r"rent[:\s]*(\d[\d\s]*)\s*€",  # English: rent: 1200 €
            r"(\d[\d\s]*)\s*eur(?:o|os)?(?:\s*/\s*(?:kk|month))?",  # 1200 euro/kk
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 100 <= price <= 10000:  # Reasonable rent range
                        data["price_eur"] = price
                        break
                except ValueError:
                    continue

        # Surface area - Finnish: "45 m²" or "45 neliötä"
        surface_patterns = [
            r"(\d+(?:[.,]\d+)?)\s*m[²2]",
            r"(\d+(?:[.,]\d+)?)\s*neliö",  # neliö = square meter
            r"pinta-ala[:\s]*(\d+(?:[.,]\d+)?)",  # pinta-ala = surface area
        ]
        for pattern in surface_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                surface_str = match.group(1).replace(",", ".")
                try:
                    data["surface_m2"] = float(surface_str)
                    break
                except ValueError:
                    continue

        # Rooms - Finnish: "3 huonetta" (3 rooms), "3h+k" (3 rooms + kitchen)
        room_patterns = [
            r"(\d+)\s*h(?:\s*\+\s*[a-z]+)?",  # 3h+k, 2h+kk
            r"(\d+)\s*huone",  # 3 huonetta
            r"(\d+)\s*room",  # English
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["rooms"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Bedrooms - Finnish: "makuuhuone" = bedroom
        bedroom_patterns = [
            r"(\d+)\s*makuuhuone",
            r"(\d+)\s*bedroom",
        ]
        for pattern in bedroom_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["bedrooms"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Address extraction from text or URL
        if "address" not in data:
            # Try to extract from URL: /vuokra-asunto/LOCATION/TYPE/ID
            url_match = re.search(r"/vuokra-asunto/([^/]+)/", url)
            if url_match:
                location = url_match.group(1).replace("-", " ").title()
                data["address"] = location

        # Finnish postal code format: 5 digits (e.g., 00100)
        postal_match = re.search(r"\b(\d{5})\b", full_text)
        if postal_match and "postal_code" not in data:
            postal = postal_match.group(1)
            # Valid Finnish postal codes start with 0-9
            if postal.startswith(("00", "01", "02", "03", "04", "05")):  # Helsinki metro area
                data["postal_code"] = postal

        # Floor - Finnish: "kerros" = floor
        floor_patterns = [
            r"(\d+)[\.\s]*kerros",  # 3. kerros, 3 kerros
            r"kerros[:\s]*(\d+)",
            r"floor[:\s]*(\d+)",
        ]
        for pattern in floor_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["floor"] = match.group(1)
                break

        # Energy label - same format as EU: A, B, C, D, E, F, G
        energy_match = re.search(r"energia(?:luokka)?[:\s]*([A-G])\b", full_text, re.IGNORECASE)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Furnished status - Finnish: "kalustettu" = furnished
        text_lower = full_text.lower()
        if "kalustettu" in text_lower or "furnished" in text_lower:
            if "ei kalustettu" in text_lower or "unfurnished" in text_lower or "kalustamaton" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"

        # Deposit - Finnish: "vakuus" or "takuuvuokra" = deposit
        deposit_patterns = [
            r"(?:vakuus|takuuvuokra|deposit)[:\s]*(\d[\d\s]*)\s*€",
            r"(\d[\d\s]*)\s*€\s*(?:vakuus|takuuvuokra|deposit)",
        ]
        for pattern in deposit_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                deposit_str = match.group(1).replace(" ", "")
                try:
                    data["deposit_eur"] = float(deposit_str)
                    break
                except ValueError:
                    continue

        # Available date - Finnish: "vapautuu" = becomes available
        avail_patterns = [
            r"(?:vapautuu|vapaa|available)[:\s]*(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
            r"(?:vapautuu|vapaa|available)[:\s]*(heti|immediately|nyt)",
        ]
        for pattern in avail_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["available_from"] = match.group(1)
                break

        # Property type from URL or text
        url_lower = url.lower()
        if "kerrostalo" in url_lower or "kerrostalo" in text_lower:
            data["property_type"] = "Apartment"
        elif "rivitalo" in url_lower or "rivitalo" in text_lower:
            data["property_type"] = "Townhouse"
        elif "omakotitalo" in url_lower or "omakotitalo" in text_lower:
            data["property_type"] = "House"
        elif "yksiö" in url_lower or "yksiö" in text_lower:
            data["property_type"] = "Studio"

        # Description - try meta description
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        # If still no description, get main content text
        if "description" not in data:
            # Look for description container
            desc_container = soup.select_one('[class*="description"], [class*="kuvaus"]')
            if desc_container:
                data["description"] = desc_container.get_text(strip=True)[:2000]

        return data
