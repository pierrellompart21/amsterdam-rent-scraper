"""Stealth scraper for Vuokraovi.com - bypasses headless browser detection.

This scraper uses undetected-chromedriver with human-like behavior to
avoid detection on Vuokraovi, which blocks standard headless browsers.

Only used when --stealth flag is passed to the CLI.
"""

import json
import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup

from amsterdam_rent_scraper.scrapers.stealth_base import StealthBaseScraper, console
from amsterdam_rent_scraper.utils.stealth_browser import StealthBrowser


class VuokraoviStealthScraper(StealthBaseScraper):
    """Stealth scraper for vuokraovi.com Finnish rental listings.

    Uses undetected-chromedriver to bypass Vuokraovi's bot detection.
    Includes Finnish locale settings and human-like behavior.
    """

    site_name = "vuokraovi"
    base_url = "https://www.vuokraovi.com"

    # Conservative delays for Vuokraovi
    STEALTH_DELAY_MIN = 4.0
    STEALTH_DELAY_MAX = 8.0

    def __init__(self, *args, **kwargs):
        # Force Finnish locale for Vuokraovi
        kwargs.setdefault("locale", "fi-FI")
        super().__init__(*args, **kwargs)

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Helsinki/Espoo area rentals."""
        base = f"{self.base_url}/vuokra-asunnot"

        params = {
            "locale": "en",  # English interface
            "pageCount": page_num,
        }

        if self.min_price:
            params["rentMin"] = self.min_price
        if self.max_price:
            params["rentMax"] = self.max_price

        return f"{base}?{urlencode(params)}"

    def get_listing_urls(self, browser: StealthBrowser) -> list[str]:
        """Scrape search results to get all listing URLs with stealth behavior."""
        urls = []
        page_num = 1
        max_pages = 2 if self.test_mode else 20

        console.print(f"  [dim]Stealth mode: using human-like delays[/]")

        while page_num <= max_pages:
            # Early exit if we have enough
            if self.max_listings and len(urls) >= self.max_listings:
                break

            search_url = self.get_search_url(page_num)
            console.print(f"  Fetching search page {page_num}: {search_url[:60]}...")

            try:
                # Navigate with stealth behavior
                browser.get(search_url, wait_for_selector='a[href*="/vuokra-asunto/"]')

                # Human-like scrolling to load lazy content
                browser.human_scroll(scroll_count=4, scroll_pause=1.5)

                # Random mouse movement
                if page_num == 1:  # First page, appear more human
                    browser.random_mouse_movement()

                html = browser.page_source
                soup = BeautifulSoup(html, "lxml")

                # Check for access denied
                if "access denied" in html.lower() or "captcha" in html.lower():
                    console.print(f"  [red]Access denied/captcha on page {page_num}[/]")
                    break

                # Extract listing URLs
                page_urls = []
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if "/vuokra-asunto/" in href:
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
                has_next = False
                next_selectors = [
                    f'a[href*="pageCount={page_num + 1}"]',
                    'button[aria-label*="Next"]',
                    'a[aria-label*="Next"]',
                ]
                for selector in next_selectors:
                    if soup.select_one(selector):
                        has_next = True
                        break

                # If full page, assume more
                if not has_next and len(page_urls) >= 20:
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
        """Parse a Vuokraovi listing page and extract data.

        This is the same parsing logic as the regular VuokraoviScraper.
        """
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Try JSON-LD structured data first
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
            h1 = soup.select_one("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)

        if "title" not in data:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Price extraction - Finnish format: "1 200 €/kk"
        price_patterns = [
            r"(\d[\d\s]*)\s*€\s*/\s*kk",
            r"(\d[\d\s]*)\s*€\s*/\s*(?:kk|kuukausi|month)",
            r"vuokra[:\s]*(\d[\d\s]*)\s*€",
            r"rent[:\s]*(\d[\d\s]*)\s*€",
            r"(\d[\d\s]*)\s*eur(?:o|os)?(?:\s*/\s*(?:kk|month))?",
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

        # Surface area
        surface_patterns = [
            r"(\d+(?:[.,]\d+)?)\s*m[²2]",
            r"(\d+(?:[.,]\d+)?)\s*neliö",
            r"pinta-ala[:\s]*(\d+(?:[.,]\d+)?)",
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

        # Rooms
        room_patterns = [
            r"(\d+)\s*h(?:\s*\+\s*[a-z]+)?",
            r"(\d+)\s*huone",
            r"(\d+)\s*room",
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["rooms"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Bedrooms
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

        # Address from URL
        if "address" not in data:
            url_match = re.search(r"/vuokra-asunto/([^/]+)/", url)
            if url_match:
                location = url_match.group(1).replace("-", " ").title()
                data["address"] = location

        # Finnish postal code
        postal_match = re.search(r"\b(\d{5})\b", full_text)
        if postal_match and "postal_code" not in data:
            postal = postal_match.group(1)
            if postal.startswith(("00", "01", "02", "03", "04", "05")):
                data["postal_code"] = postal

        # Floor
        floor_patterns = [
            r"(\d+)[\.\s]*kerros",
            r"kerros[:\s]*(\d+)",
            r"floor[:\s]*(\d+)",
        ]
        for pattern in floor_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["floor"] = match.group(1)
                break

        # Energy label
        energy_match = re.search(r"energia(?:luokka)?[:\s]*([A-G])\b", full_text, re.IGNORECASE)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Furnished status
        text_lower = full_text.lower()
        if "kalustettu" in text_lower or "furnished" in text_lower:
            if "ei kalustettu" in text_lower or "unfurnished" in text_lower or "kalustamaton" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"

        # Deposit
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

        # Available date
        avail_patterns = [
            r"(?:vapautuu|vapaa|available)[:\s]*(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
            r"(?:vapautuu|vapaa|available)[:\s]*(heti|immediately|nyt)",
        ]
        for pattern in avail_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["available_from"] = match.group(1)
                break

        # Property type
        url_lower = url.lower()
        if "kerrostalo" in url_lower or "kerrostalo" in text_lower:
            data["property_type"] = "Apartment"
        elif "rivitalo" in url_lower or "rivitalo" in text_lower:
            data["property_type"] = "Townhouse"
        elif "omakotitalo" in url_lower or "omakotitalo" in text_lower:
            data["property_type"] = "House"
        elif "yksiö" in url_lower or "yksiö" in text_lower:
            data["property_type"] = "Studio"

        # Description
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        if "description" not in data:
            desc_container = soup.select_one('[class*="description"], [class*="kuvaus"]')
            if desc_container:
                data["description"] = desc_container.get_text(strip=True)[:2000]

        return data
