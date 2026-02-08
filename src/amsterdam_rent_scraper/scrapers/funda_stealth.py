"""Stealth scraper for Funda.nl - bypasses aggressive anti-bot protection.

This scraper uses undetected-chromedriver with human-like behavior to
avoid detection on Funda, which has strong anti-bot measures.

Only used when --stealth flag is passed to the CLI.
"""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from amsterdam_rent_scraper.scrapers.stealth_base import StealthBaseScraper, console
from amsterdam_rent_scraper.utils.stealth_browser import StealthBrowser


class FundaStealthScraper(StealthBaseScraper):
    """Stealth scraper for funda.nl rental listings.

    Uses undetected-chromedriver to bypass Funda's anti-bot measures.
    Includes extra delays and human-like behavior.
    """

    site_name = "funda"
    base_url = "https://www.funda.nl"

    # Extra conservative delays for Funda
    STEALTH_DELAY_MIN = 5.0
    STEALTH_DELAY_MAX = 10.0

    def __init__(self, *args, **kwargs):
        # Force Dutch locale for Funda
        kwargs.setdefault("locale", "nl-NL")
        super().__init__(*args, **kwargs)

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Amsterdam rentals."""
        url = (
            f"{self.base_url}/zoeken/huur"
            f"?selected_area=%5B%22amsterdam%22%5D"
            f"&price=%22{self.min_price}-{self.max_price}%22"
            f"&availability=%5B%22available%22%5D"
        )
        if page_num > 1:
            url += f"&search_result={page_num}"
        return url

    def get_listing_urls(self, browser: StealthBrowser) -> list[str]:
        """Scrape search results to get all listing URLs with stealth behavior."""
        urls = []
        page_num = 1
        max_pages = 2 if self.test_mode else 10

        console.print(f"  [dim]Stealth mode: using human-like delays[/]")

        while page_num <= max_pages:
            # Early exit if we have enough
            if self.max_listings and len(urls) >= self.max_listings:
                break

            search_url = self.get_search_url(page_num)
            console.print(f"  Fetching search page {page_num}: {search_url[:60]}...")

            try:
                # Navigate with stealth behavior
                browser.get(search_url, wait_for_selector='a[href*="/huur/"]')

                # Human-like scrolling to trigger lazy loading
                browser.human_scroll(scroll_count=4, scroll_pause=2.0)

                # Random mouse movement to appear more human
                browser.random_mouse_movement()

                html = browser.page_source
                soup = BeautifulSoup(html, "lxml")

                # Check for blocked/captcha page
                if "access denied" in html.lower() or "captcha" in html.lower():
                    console.print(f"  [red]Access denied/captcha on page {page_num}[/]")
                    break

                # Check if we're being rate limited
                if "too many requests" in html.lower() or "rate limit" in html.lower():
                    console.print(f"  [yellow]Rate limited, waiting longer...[/]")
                    browser.wait_for_timeout(30000)  # 30 second wait
                    continue

                # Extract listing URLs
                page_urls = []
                for link in soup.select('a[href*="/huur/"]'):
                    href = link.get("href", "")
                    # Match rental listing URLs
                    if re.search(r"/huur/[^/]+/(appartement|woning|kamer|studio)-\d+", href):
                        full_url = urljoin(self.base_url, href)
                        # Avoid duplicates and media URLs
                        if full_url not in urls and full_url not in page_urls:
                            if not any(x in full_url for x in ["/media/", "/foto/", "/plattegrond/"]):
                                page_urls.append(full_url)

                if not page_urls:
                    console.print(f"  No listings found on page {page_num}")
                    break

                urls.extend(page_urls)
                console.print(f"  Page {page_num}: found {len(page_urls)} links (total: {len(urls)})")

                # Check for next page
                has_next = soup.select_one('[class*="pagination"] a[rel="next"]') or \
                          soup.select_one(f'a[href*="search_result={page_num + 1}"]')
                if not has_next:
                    break

                page_num += 1

                # Extra delay between search pages
                self._delay(min_delay=4.0, max_delay=8.0)

            except Exception as e:
                console.print(f"  [red]Error on page {page_num}: {e}[/]")
                break

        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Funda listing page and extract data.

        This is the same parsing logic as the regular FundaScraper.
        """
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Try to find JSON-LD structured data first
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                if isinstance(ld_data, dict):
                    if ld_data.get("@type") == "Product" or ld_data.get("@type") == "Residence":
                        if "name" in ld_data:
                            data["title"] = ld_data["name"]
                        if "description" in ld_data:
                            data["description"] = ld_data["description"][:2000]
                        if "address" in ld_data:
                            addr = ld_data["address"]
                            if isinstance(addr, dict):
                                parts = [addr.get("streetAddress", ""),
                                        addr.get("postalCode", ""),
                                        addr.get("addressLocality", "")]
                                data["address"] = " ".join(p for p in parts if p)
                                if addr.get("postalCode"):
                                    data["postal_code"] = addr["postalCode"].replace(" ", "")
                        if "offers" in ld_data:
                            offer = ld_data["offers"]
                            if isinstance(offer, dict) and "price" in offer:
                                try:
                                    data["price_eur"] = float(offer["price"])
                                except (ValueError, TypeError):
                                    pass
            except (json.JSONDecodeError, TypeError):
                continue

        # Title fallback
        if "title" not in data:
            title_el = soup.select_one("h1, .object-header__title")
            if title_el:
                data["title"] = title_el.get_text(strip=True)

        # Price fallback
        if "price_eur" not in data:
            price_patterns = ['.object-header__price', '.price', '[class*="price"]']
            for pattern in price_patterns:
                for el in soup.select(pattern):
                    price_text = el.get_text(strip=True)
                    price_match = re.search(r"€\s*([\d.]+)", price_text)
                    if price_match:
                        price_str = price_match.group(1).replace(".", "")
                        try:
                            price = float(price_str)
                            if 500 <= price <= 15000:
                                data["price_eur"] = price
                                break
                        except ValueError:
                            continue
                if "price_eur" in data:
                    break

        # Address fallback
        if "address" not in data:
            address_el = soup.select_one('.object-header__address, .object-header__subtitle')
            if address_el:
                data["address"] = address_el.get_text(strip=True)

        # Extract details from kenmerken (characteristics) section
        full_text = soup.get_text()

        # Surface area
        surface_patterns = [
            r"woonoppervlakte[:\s]*(\d+)\s*m",
            r"oppervlakte[:\s]*(\d+)\s*m",
            r"(\d+)\s*m[²2]",
        ]
        for pattern in surface_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["surface_m2"] = float(match.group(1))
                break

        # Rooms/bedrooms
        rooms_patterns = [
            r"aantal kamers[:\s]*(\d+)",
            r"(\d+)\s*kamer",
            r"(\d+)\s*slaapkamer",
        ]
        for pattern in rooms_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["rooms"] = int(match.group(1))
                break

        # Bedrooms specifically
        bedroom_match = re.search(r"(\d+)\s*slaapkamer", full_text, re.IGNORECASE)
        if bedroom_match:
            data["bedrooms"] = int(bedroom_match.group(1))

        # Bathrooms
        bathroom_match = re.search(r"(\d+)\s*badkamer", full_text, re.IGNORECASE)
        if bathroom_match:
            data["bathrooms"] = int(bathroom_match.group(1))

        # Furnished status
        text_lower = full_text.lower()
        if "gemeubileerd" in text_lower:
            if "ongemeubileerd" in text_lower or "niet gemeubileerd" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"
        elif "gestoffeerd" in text_lower:
            data["furnished"] = "Upholstered"
        elif "kaal" in text_lower:
            data["furnished"] = "Shell"

        # Energy label
        energy_match = re.search(r"energielabel[:\s]*([A-G]\+*)", full_text, re.IGNORECASE)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Description
        if "description" not in data:
            desc_el = soup.select_one('.object-description__content, .description')
            if desc_el:
                data["description"] = desc_el.get_text(strip=True)[:2000]

        # Postal code from address
        if "postal_code" not in data and "address" in data:
            postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", data["address"])
            if postal_match:
                data["postal_code"] = postal_match.group(1).replace(" ", "")

        return data
