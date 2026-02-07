"""Lumo.fi scraper - Kojamo/Lumo rental apartments (React/Redux, JavaScript rendered)."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class LumoScraper(PlaywrightBaseScraper):
    """Scraper for lumo.fi Finnish rental listings.

    Lumo is owned by Kojamo, one of Finland's largest rental housing companies.
    They have ~39,000 apartments across Finland.
    The site is React/Redux-based and requires JavaScript rendering.

    URL patterns:
    - Search: https://lumo.fi/vuokra-asunnot
    - Listing: https://lumo.fi/vuokra-asunnot/{City}/{District}/{Address}/{Unit-ID}

    Note: The site shows all Finnish cities by default. We filter for Helsinki
    metropolitan area (Helsinki, Espoo, Vantaa, Kauniainen) in get_listing_urls.
    """

    site_name = "lumo"
    base_url = "https://lumo.fi"

    # Helsinki metropolitan area cities (case-insensitive matching)
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
        # Block images only (keep scripts/CSS for React rendering)
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self) -> str:
        """Return the main search URL for Lumo apartments."""
        return f"{self.base_url}/vuokra-asunnot"

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs (CybotCookiebot)."""
        try:
            # CybotCookiebot is used on lumo.fi
            consent_selectors = [
                '#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll',  # Cybot "Allow all"
                '#CybotCookiebotDialogBodyButtonAccept',  # Cybot "Accept"
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
                        page.wait_for_timeout(2000)
                        console.print("  [dim]Cookie consent handled[/]")
                        return
                except Exception:
                    continue
        except Exception:
            pass

    def _is_helsinki_area(self, url: str) -> bool:
        """Check if a listing URL is in the Helsinki metropolitan area."""
        # URL pattern: /vuokra-asunnot/{City}/{District}/...
        url_lower = url.lower()
        for city in self.HELSINKI_METRO_CITIES:
            if f"/vuokra-asunnot/{city}/" in url_lower:
                return True
        return False

    def _click_show_more(self, page: Page) -> bool:
        """Click 'Show more' button to load additional listings. Returns True if clicked."""
        try:
            # Finnish: "Näytä lisää asuntoja" (Show more apartments)
            show_more_selectors = [
                'button:has-text("Näytä lisää")',
                'button:has-text("Show more")',
                'button:has-text("Lataa lisää")',
                '[data-testid="load-more"]',
            ]
            for selector in show_more_selectors:
                try:
                    btn = page.locator(selector)
                    if btn.count() > 0 and btn.first.is_visible():
                        btn.first.click()
                        page.wait_for_timeout(3000)  # Wait for new content
                        return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs for Helsinki area."""
        urls = []
        seen_ids = set()

        search_url = self.get_search_url()
        console.print(f"  Fetching: {search_url}")

        try:
            # Navigate to search page
            page.goto(search_url, wait_until="networkidle", timeout=60000)
            self._handle_cookie_consent(page)

            # Wait for React to render content
            page.wait_for_timeout(5000)

            # Try waiting for apartment cards to appear
            try:
                page.wait_for_selector('a[href*="/vuokra-asunnot/"]', timeout=15000)
            except Exception:
                console.print("  [yellow]Could not find listing links, trying anyway...[/]")

            # Load more listings by clicking "Show more" button multiple times
            # until we have enough Helsinki area listings or button disappears
            max_clicks = 20  # Limit to avoid infinite loop
            helsinki_count = 0
            for _ in range(max_clicks):
                # Extract current listings
                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # Count Helsinki area listings
                helsinki_count = 0
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if "/vuokra-asunnot/" in href and self._is_helsinki_area(href):
                        helsinki_count += 1

                # Check if we have enough Helsinki area listings
                if self.max_listings and helsinki_count >= self.max_listings:
                    console.print(f"  Found {helsinki_count} Helsinki area listings")
                    break

                # Try to load more
                if not self._click_show_more(page):
                    console.print(f"  No more 'show more' button, stopping pagination")
                    break

            # Final extraction of all listing URLs
            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                # Match apartment listing URLs
                # Pattern: /vuokra-asunnot/{City}/{District}/{Address}/{Unit-ID}
                if "/vuokra-asunnot/" in href and href.count("/") >= 4:
                    # Skip if it's just the search page or category page
                    if href == "/vuokra-asunnot" or href.endswith("/vuokra-asunnot/"):
                        continue

                    # Filter for Helsinki metropolitan area
                    if not self._is_helsinki_area(href):
                        continue

                    # Extract a unique ID from the URL (last path segment)
                    listing_id = href.rstrip("/").split("/")[-1]
                    if listing_id and listing_id not in seen_ids:
                        seen_ids.add(listing_id)
                        full_url = urljoin(self.base_url, href)
                        urls.append(full_url)

            console.print(f"  Found {len(urls)} Helsinki area apartment listings")

        except Exception as e:
            console.print(f"  [red]Error loading listings: {e}[/]")
            import traceback
            console.print(f"  [dim]{traceback.format_exc()}[/]")

        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Lumo listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Get full text for regex extraction
        full_text = soup.get_text(" ", strip=True)

        # Title from h1 or og:title
        h1 = soup.select_one("h1")
        if h1:
            data["title"] = h1.get_text(strip=True)

        if "title" not in data:
            og_title = soup.select_one('meta[property="og:title"]')
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]

        # Extract address from URL
        # Pattern: /vuokra-asunnot/{City}/{District}/{Street}/{Unit}
        url_match = re.search(
            r"/vuokra-asunnot/([^/]+)/([^/]+)/([^/]+)/([^/]+)$",
            url, re.IGNORECASE
        )
        if url_match:
            city = url_match.group(1).replace("-", " ").title()
            district = url_match.group(2).replace("-", " ").title()
            street = url_match.group(3).replace("-", " ").title()
            unit = url_match.group(4).replace("-", " ")
            data["address"] = f"{street}, {district}, {city}"
            data["neighborhood"] = district

        # Price - Finnish format: "X €/kk" (euros per month)
        price_patterns = [
            r"(\d[\d\s]*)\s*€\s*/\s*(?:kk|kuukausi|month)",  # 798 €/kk
            r"vuokra[:\s]*(\d[\d\s]*)\s*€",  # vuokra: 798 €
            r"(\d{3,4})\s*€",  # 798 € (3-4 digit price)
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 300 <= price <= 5000:  # Reasonable rent range
                        data["price_eur"] = price
                        break
                except ValueError:
                    continue

        # Surface area - "X m²"
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
                    if 10 <= surface <= 500:  # Reasonable size
                        data["surface_m2"] = surface
                        break
                except ValueError:
                    continue

        # Rooms - Finnish format: "1H+KT" (1 room + kitchen), "2H+K" (2 rooms + kitchen)
        room_patterns = [
            r"(\d+)\s*[Hh]\s*\+",  # 2H+K or 2h+kt
            r"(\d+)\s*huone",  # 2 huonetta (2 rooms)
        ]
        for pattern in room_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                try:
                    data["rooms"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Floor - "X/Y kerros" (floor X of Y) or "X. kerros" (Xth floor)
        floor_patterns = [
            r"(\d+)\s*/\s*\d+\s*kerros",  # 3/5 kerros
            r"(\d+)[\.\s]*kerros",  # 3. kerros
            r"kerros[:\s]*(\d+)",  # kerros: 3
        ]
        for pattern in floor_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["floor"] = match.group(1)
                break

        # Finnish postal code (5 digits, starting with 00/01/02 for Helsinki metro)
        postal_match = re.search(r"\b(\d{5})\b", full_text)
        if postal_match:
            postal = postal_match.group(1)
            # Helsinki metro area codes: 00xxx Helsinki, 01xxx Vantaa, 02xxx Espoo
            if postal[:2] in ("00", "01", "02"):
                data["postal_code"] = postal

        # Elevator
        if re.search(r"\bhissi\b", full_text, re.IGNORECASE):
            data["has_elevator"] = True

        # Sauna - very common in Finnish apartments
        if re.search(r"\bsauna\b", full_text, re.IGNORECASE):
            data["has_sauna"] = True

        # Balcony
        if re.search(r"\b(parveke|balcony)\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True

        # Availability - "Vapautuu X.X.XXXX" or "Heti vuokrattavissa"
        avail_patterns = [
            r"vapautuu[:\s]*(\d{1,2}[./]\d{1,2}[./]\d{2,4})",
            r"vapautuu[:\s]*(\d{1,2}\.\s*\d{1,2}\.\s*\d{4})",
            r"(heti\s*vuokrattavissa)",
            r"(immediately available)",
        ]
        for pattern in avail_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["available_from"] = match.group(1).strip()
                break

        # Description from meta or page content
        desc_el = soup.select_one('meta[name="description"]')
        if desc_el and desc_el.get("content"):
            data["description"] = desc_el["content"][:2000]

        # Property type - Lumo mainly has apartments
        data["property_type"] = "Apartment"

        # Energy label
        energy_match = re.search(r"energia(?:luokka)?[:\s]*([A-G])\b", full_text, re.IGNORECASE)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        return data
