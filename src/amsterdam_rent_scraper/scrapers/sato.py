"""SATO.fi scraper - major Finnish rental company (JavaScript rendered)."""

import json
import re
from urllib.parse import urljoin, quote

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class SatoScraper(PlaywrightBaseScraper):
    """Scraper for sato.fi Finnish rental listings.

    SATO is one of the largest rental housing companies in Finland.
    The site is Next.js-based and requires JavaScript rendering.
    URL pattern: /fi/vuokra-asunnot/{city}/{area}/{address}/{building-id}/asunto/{apartment-id}
    """

    site_name = "sato"
    base_url = "https://www.sato.fi"

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
        # Block images only
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self) -> str:
        """Build search URL for Helsinki metropolitan area rentals.

        SATO has listings in Helsinki, Espoo, Vantaa (Greater Helsinki).
        """
        # Base search page shows all SATO rentals
        return f"{self.base_url}/vuokra-asunnot"

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []

        search_url = self.get_search_url()
        console.print(f"  Fetching: {search_url}")

        try:
            # Navigate and wait for content
            page.goto(search_url, wait_until="networkidle", timeout=60000)

            # Handle cookie consent if it appears
            try:
                consent_btn = page.locator('button:has-text("Hyväksy kaikki"), button:has-text("Accept all")')
                if consent_btn.count() > 0:
                    consent_btn.first.click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            # Wait for listings to load
            page.wait_for_timeout(5000)

            # Scroll to load all content
            prev_count = 0
            for scroll_attempt in range(10):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

                # Check if we have enough or no new content
                html = page.content()
                soup = BeautifulSoup(html, "lxml")
                links = [l for l in soup.find_all("a", href=True)
                        if "/asunto/" in l.get("href", "")]

                current_count = len(links)
                if current_count == prev_count:
                    # No new content loaded
                    break
                prev_count = current_count

                if self.max_listings and current_count >= self.max_listings:
                    break

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Find apartment links
            # Pattern: /fi/vuokra-asunnot/{city}/{area}/{address}/{building-id}/asunto/{apartment-id}
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if "/asunto/" in href and "/vuokra-asunnot/" in href:
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            console.print(f"  Found {len(urls)} apartment links")

            # Filter for Helsinki metropolitan area (Helsinki, Espoo, Vantaa)
            helsinki_area = []
            for url in urls:
                url_lower = url.lower()
                if any(city in url_lower for city in ["helsinki", "espoo", "vantaa"]):
                    helsinki_area.append(url)

            if helsinki_area:
                console.print(f"  Filtered to {len(helsinki_area)} Helsinki area listings")
                urls = helsinki_area

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")

        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a SATO listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Get full text for regex extraction
        full_text = soup.get_text(" ", strip=True)

        # Try JSON-LD structured data
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    if item.get("@type") in ["Apartment", "House", "Product", "Residence"]:
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

        # Title from h1 or og:title
        if "title" not in data:
            h1 = soup.select_one("h1")
            if h1:
                data["title"] = h1.get_text(strip=True)

        if "title" not in data:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Extract address from URL if not found
        # Pattern: /vuokra-asunnot/{city}/{area}/{street-address}/
        if "address" not in data:
            url_match = re.search(
                r"/vuokra-asunnot/([^/]+)/([^/]+)/([^/]+)/",
                url, re.IGNORECASE
            )
            if url_match:
                city = url_match.group(1).replace("%20", " ").title()
                area = url_match.group(2).replace("-", " ").replace("%20", " ").title()
                street = url_match.group(3).replace("%20", " ").title()
                data["address"] = f"{street}, {area}, {city}"

        # Price - Finnish format: "X €/kk" or "X eur/kk"
        price_patterns = [
            r"vuokra[:\s]*(\d[\d\s]*)\s*€",  # vuokra: 1200 €
            r"(\d[\d\s]*)\s*€\s*/\s*(?:kk|kuukausi)",  # 1200 €/kk
            r"(\d[\d\s,\.]+)\s*eur(?:o|os)?\s*/\s*kk",  # 1200 euro/kk
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "").replace(",", ".")
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

        # Rooms - Finnish format: "2h+k" (2 rooms + kitchen)
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

        # Floor
        floor_patterns = [
            r"(\d+)[\.\s]*kerros",
            r"kerros[:\s]*(\d+)",
        ]
        for pattern in floor_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["floor"] = match.group(1)
                break

        # Finnish postal code (5 digits)
        if "postal_code" not in data:
            postal_match = re.search(r"\b(\d{5})\b", full_text)
            if postal_match:
                postal = postal_match.group(1)
                # Helsinki metro area codes start with 00, 01, 02
                if postal[:2] in ("00", "01", "02"):
                    data["postal_code"] = postal

        # Energy label
        energy_match = re.search(r"energia(?:luokka)?[:\s]*([A-G])\b", full_text, re.IGNORECASE)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Building year
        year_match = re.search(r"(?:rakennus)?vuosi[:\s]*(\d{4})", full_text, re.IGNORECASE)
        if year_match:
            data["year_built"] = int(year_match.group(1))

        # Sauna - very common in Finnish apartments
        if "sauna" in full_text.lower():
            data["has_sauna"] = True

        # Balcony
        if "parveke" in full_text.lower() or "balcony" in full_text.lower():
            data["has_balcony"] = True

        # Available date
        avail_patterns = [
            r"(?:vapautuu|vapaa)[:\s]*(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
            r"(?:vapautuu|vapaa)[:\s]*(heti|immediately)",
        ]
        for pattern in avail_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["available_from"] = match.group(1)
                break

        # Description
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        # Property type - SATO mainly has apartments
        data["property_type"] = "Apartment"

        return data
