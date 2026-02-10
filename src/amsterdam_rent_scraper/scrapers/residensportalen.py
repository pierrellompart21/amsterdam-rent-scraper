"""Residensportalen.se scraper - Swedish estate agent rental portal."""

import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class ResidensportalenScraper(PlaywrightBaseScraper):
    """Scraper for residensportalen.com rental listings.

    Residensportalen is run by Sweden's leading estate agents, offering
    direct contact with landlords and no hidden fees.

    URL patterns:
    - Search: https://www.residensportalen.com/objects/stockholm/stockholm/
    - Listing: /objects/stockholm/stockholm/{property-name}-{id}/
    """

    site_name = "residensportalen"
    base_url = "https://www.residensportalen.com"

    def _new_page(self) -> Page:
        """Create a new page with Swedish locale settings."""
        browser = self._get_browser()
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="sv-SE",
        )
        page = context.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,webp}", lambda route: route.abort())
        return page

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Stockholm rentals."""
        base = f"{self.base_url}/objects/stockholm/stockholm/"
        params = {}
        if self.min_price:
            params["rent_from"] = int(self.min_price)
        if self.max_price:
            params["rent_to"] = int(self.max_price)
        if page_num > 1:
            params["page"] = page_num
        if params:
            return f"{base}?{urlencode(params)}"
        return base

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs."""
        try:
            consent_selectors = [
                'button:has-text("Accept")',
                'button:has-text("Acceptera")',
                'button:has-text("Godkänn")',
                'button:has-text("Allow")',
                '#accept-cookies',
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

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs with pagination."""
        urls = []
        seen_ids = set()
        current_page = 1
        max_pages = 15

        console.print(f"  Starting search on {self.site_name}...")

        while current_page <= max_pages:
            try:
                page_url = self.get_search_url(current_page)
                console.print(f"  Fetching page {current_page}: {page_url}")

                page.goto(page_url, wait_until="networkidle", timeout=60000)

                if current_page == 1:
                    self._handle_cookie_consent(page)

                page.wait_for_timeout(3000)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # Find listing links
                listing_links = soup.find_all("a", href=re.compile(r"/objects/stockholm/.+/.+"))

                if not listing_links:
                    console.print(f"  No listings found on page {current_page}")
                    break

                new_urls = 0
                for link in listing_links:
                    href = link.get("href", "")
                    # Skip category pages
                    if href.endswith("/stockholm/") or href.count("/") < 4:
                        continue
                    # Extract ID to deduplicate
                    id_match = re.search(r"-(\d+)/?$", href)
                    if id_match:
                        listing_id = id_match.group(1)
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            full_url = urljoin(self.base_url, href)
                            urls.append(full_url)
                            new_urls += 1
                    else:
                        # Use full path as ID if no numeric ID
                        if href not in seen_ids:
                            seen_ids.add(href)
                            full_url = urljoin(self.base_url, href)
                            urls.append(full_url)
                            new_urls += 1

                console.print(f"  Page {current_page}: Found {new_urls} new listings")

                if new_urls == 0:
                    break

                # Check for next page
                next_link = soup.find("a", href=re.compile(rf"page={current_page + 1}"))
                next_btn = soup.find("a", class_=re.compile(r"next"))
                if not next_link and not next_btn:
                    break

                current_page += 1

            except Exception as e:
                console.print(f"  [red]Error on page {current_page}: {e}[/]")
                break

        console.print(f"  Total: Found {len(urls)} listing URLs")
        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Residensportalen listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Title
        title_tag = soup.find("h1")
        if title_tag:
            data["title"] = title_tag.get_text(strip=True)

        # Price - Swedish format
        price_patterns = [
            r"(\d{1,3}(?:[\s\u00a0]\d{3})*)\s*(?:kr|SEK)(?:/månad|/mån|/month)?",
            r"(?:Hyra|Rent|Monthly)[:\s]*(\d{1,3}(?:[\s\u00a0]\d{3})*)",
        ]
        for pattern in price_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                try:
                    price = float(price_str)
                    if 3000 <= price <= 100000:
                        data["price_sek"] = price
                        data["price_eur"] = round(price / 11.5, 2)
                        break
                except ValueError:
                    continue

        # Surface area
        surface_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m²|m2|kvm|sqm)", full_text, re.IGNORECASE)
        if surface_match:
            try:
                data["surface_m2"] = float(surface_match.group(1).replace(",", "."))
            except ValueError:
                pass

        # Rooms
        room_match = re.search(r"(\d+)\s*(?:rum|rok|rooms?)\b", full_text, re.IGNORECASE)
        if room_match:
            try:
                data["rooms"] = int(room_match.group(1))
            except ValueError:
                pass

        # Address - often in the title or specific element
        addr_tag = soup.find(class_=re.compile(r"address|location|street", re.IGNORECASE))
        if addr_tag:
            data["address"] = addr_tag.get_text(strip=True)
        else:
            # Try to extract from title or URL
            addr_match = re.search(r"([A-ZÄÖÅ][a-zäöå]+(?:gatan|vägen|gränd|plan|gata)\s*\d*)", full_text)
            if addr_match:
                data["address"] = f"{addr_match.group(1)}, Stockholm"

        # Postal code
        postal_match = re.search(r"\b(\d{3})\s*(\d{2})\b", full_text)
        if postal_match:
            data["postal_code"] = f"{postal_match.group(1)} {postal_match.group(2)}"

        # Floor
        floor_match = re.search(r"(\d+)(?::a|:e)?\s*(?:våning|floor)", full_text, re.IGNORECASE)
        if floor_match:
            data["floor"] = floor_match.group(1)

        # Available date
        if re.search(r"omgående|immediately|per direct", full_text, re.IGNORECASE):
            data["available_date"] = "Immediately"
        else:
            date_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})", full_text)
            if date_match:
                data["available_date"] = date_match.group(1)

        # Features
        if re.search(r"\bbalkong|balcony\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True
        if re.search(r"\bhiss|elevator\b", full_text, re.IGNORECASE):
            data["has_elevator"] = True
        if re.search(r"\bmöbler|furnished\b", full_text, re.IGNORECASE):
            data["is_furnished"] = True
        if re.search(r"\bparkering|garage|parking\b", full_text, re.IGNORECASE):
            data["has_parking"] = True

        # Agency info
        agency_tag = soup.find(class_=re.compile(r"agent|agency|broker|landlord", re.IGNORECASE))
        if agency_tag:
            data["agency"] = agency_tag.get_text(strip=True)

        data["property_type"] = "Apartment"
        return data
