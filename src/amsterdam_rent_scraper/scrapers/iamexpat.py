"""IamExpat.nl housing scraper - requires JavaScript for listings."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class IamExpatScraper(PlaywrightBaseScraper):
    """Scraper for iamexpat.nl housing listings (JavaScript required, Next.js site)."""

    site_name = "iamexpat"
    base_url = "https://www.iamexpat.nl"

    def fetch_page(self, url: str, page=None, wait_selector: str | None = None) -> str:
        """Fetch a page with JavaScript rendering - optimized for Next.js sites."""
        close_page = page is None
        if page is None:
            page = self._new_page()

        try:
            # Use domcontentloaded instead of networkidle for Next.js sites
            # networkidle can hang on sites with persistent connections
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for content to be visible - look for common content selectors
            try:
                page.wait_for_selector("h1, h2, [class*='price'], [class*='rent']", timeout=10000)
            except Exception:
                pass  # Continue even if selector not found

            # Small delay for dynamic content
            page.wait_for_timeout(2000)

            return page.content()
        finally:
            if close_page:
                page.close()

    def get_search_url(self, page_num: int = 1) -> str:
        """Build search URL for Amsterdam rentals."""
        # IamExpat URL structure: /housing/rentals/amsterdam
        # Price filtering via query params: minPrice, maxPrice
        url = f"{self.base_url}/housing/rentals/amsterdam"
        params = []
        if self.min_price:
            params.append(f"minPrice={self.min_price}")
        if self.max_price:
            params.append(f"maxPrice={self.max_price}")
        if page_num > 1:
            params.append(f"page={page_num}")
        if params:
            url += "?" + "&".join(params)
        return url

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page_num = 1
        max_pages = 2 if self.test_mode else 50  # Safety limit

        while page_num <= max_pages:
            # Early exit if we have enough listings
            if self.max_listings is not None and len(urls) >= self.max_listings:
                break

            search_url = self.get_search_url(page_num)
            console.print(f"  Fetching search page {page_num}: {search_url[:80]}...")

            try:
                # Use domcontentloaded - networkidle can hang on Next.js sites
                page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                # Wait for listing links to appear
                try:
                    page.wait_for_selector('a[href*="/housing/rental-properties/"]', timeout=10000)
                except Exception:
                    pass
                page.wait_for_timeout(3000)

                # Scroll to load any lazy content
                for _ in range(2):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1500)

                html = page.content()
                soup = BeautifulSoup(html, "lxml")

                # IamExpat listing URLs pattern: /housing/rental-properties/amsterdam/TYPE/ID
                # Types: apartment, house, room, studio
                page_urls = []
                for link in soup.select('a[href*="/housing/rental-properties/amsterdam/"]'):
                    href = link.get("href", "")
                    # Match listing URLs with type and unique ID
                    if re.search(r"/housing/rental-properties/amsterdam/(apartment|house|room|studio)/[A-Za-z0-9]+$", href):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls and full_url not in page_urls:
                            page_urls.append(full_url)

                if not page_urls:
                    console.print(f"  No listings found on page {page_num}")
                    break

                urls.extend(page_urls)
                console.print(f"  Page {page_num}: found {len(page_urls)} links")

                # Check for next page - look for pagination links
                has_next = soup.select_one(f'a[href*="page={page_num + 1}"]') or \
                          soup.select_one('[aria-label="Next"]') or \
                          soup.select_one('a:-soup-contains("Next")')
                if not has_next:
                    # Also check if there's a visible page number greater than current
                    page_links = soup.select('a[href*="page="]')
                    next_pages = [l for l in page_links if f"page={page_num + 1}" in l.get("href", "")]
                    if not next_pages:
                        break

                page_num += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page_num}: {e}[/]")
                break

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse an IamExpat listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Get full text for regex extraction
        full_text = soup.get_text(" ", strip=True)

        # Try JSON-LD structured data first
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    if item.get("@type") in ["Product", "Apartment", "House", "Room", "RealEstateListing"]:
                        if "name" in item:
                            data["title"] = item["name"]
                        if "description" in item:
                            data["description"] = item["description"][:2000]
                        # Check for offers/price
                        if "offers" in item:
                            offers = item["offers"]
                            if isinstance(offers, dict) and "price" in offers:
                                try:
                                    data["price_eur"] = float(offers["price"])
                                except (ValueError, TypeError):
                                    pass
            except (json.JSONDecodeError, TypeError):
                continue

        # Title - try page title and headings
        if "title" not in data:
            # Try meta title
            title_el = soup.select_one('meta[property="og:title"]')
            if title_el and title_el.get("content"):
                data["title"] = title_el["content"]

        if "title" not in data:
            # Try h1 or h2
            for heading in soup.select("h1, h2"):
                text = heading.get_text(strip=True)
                if text and len(text) > 5 and "iamexpat" not in text.lower():
                    data["title"] = text
                    break

        # Fallback: derive title from URL
        # URL pattern: /housing/rental-properties/amsterdam/TYPE/ID
        if "title" not in data:
            url_match = re.search(r"/housing/rental-properties/amsterdam/(\w+)/", url)
            if url_match:
                prop_type = url_match.group(1).replace("-", " ").title()
                data["title"] = f"{prop_type} in Amsterdam"

        # Price extraction - look for EUR patterns
        if "price_eur" not in data:
            # Pattern: €2,000 or €2.000 or € 2000
            price_patterns = [
                r"€\s*([\d.,]+)\s*(?:per month|p\.?m\.?|/month|monthly)?",
                r"rent[:\s]*([\d.,]+)\s*€",
                r"([\d.,]+)\s*€\s*(?:per month|p\.?m\.?)",
            ]
            for pattern in price_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(".", "").replace(",", ".")
                    # Remove trailing dot if present
                    price_str = price_str.rstrip(".")
                    try:
                        price = float(price_str)
                        if 100 <= price <= 15000:
                            data["price_eur"] = price
                            break
                    except ValueError:
                        continue

        # Surface area
        surface_match = re.search(r"(\d+)\s*m[²2]", full_text)
        if surface_match:
            data["surface_m2"] = float(surface_match.group(1))

        # Rooms/Bedrooms - look for explicit counts
        bedroom_match = re.search(r"(\d+)\s*(?:bedroom|slaapkamer|bed)", full_text, re.IGNORECASE)
        if bedroom_match:
            data["bedrooms"] = int(bedroom_match.group(1))

        rooms_match = re.search(r"(\d+)\s*(?:room|kamer)(?:s)?\b", full_text, re.IGNORECASE)
        if rooms_match:
            data["rooms"] = int(rooms_match.group(1))

        # Bathrooms
        bath_match = re.search(r"(\d+)\s*(?:bathroom|badkamer)", full_text, re.IGNORECASE)
        if bath_match:
            data["bathrooms"] = int(bath_match.group(1))

        # Property type from URL
        if "/apartment/" in url:
            data["property_type"] = "Apartment"
        elif "/house/" in url:
            data["property_type"] = "House"
        elif "/room/" in url:
            data["property_type"] = "Room"
        elif "/studio/" in url:
            data["property_type"] = "Studio"

        # Address extraction
        # Look for street name patterns
        address_patterns = [
            r"(?:address|located at|street)[:\s]*([A-Za-z\s]+(?:straat|weg|plein|laan|gracht|kade|singel))",
            r"([A-Za-z\s]+(?:straat|weg|plein|laan|gracht|kade|singel))[,\s]+amsterdam",
        ]
        for pattern in address_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                data["address"] = match.group(1).strip() + ", Amsterdam"
                break

        # Try to extract address from title if it contains street name
        if "address" not in data and "title" in data:
            street_match = re.search(
                r"([A-Za-z\s]+(?:straat|weg|plein|laan|gracht|kade|singel))",
                data["title"],
                re.IGNORECASE
            )
            if street_match:
                data["address"] = street_match.group(1).strip() + ", Amsterdam"

        # Fallback address
        if "address" not in data:
            data["address"] = "Amsterdam"

        # Postal code - Dutch format: 1234AB
        postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
        if postal_match:
            data["postal_code"] = postal_match.group(1).replace(" ", "")

        # Furnished status
        text_lower = full_text.lower()
        if "furnished" in text_lower:
            if "unfurnished" in text_lower or "not furnished" in text_lower:
                data["furnished"] = "Unfurnished"
            else:
                data["furnished"] = "Furnished"
        elif "gemeubileerd" in text_lower:
            data["furnished"] = "Furnished"
        elif "gestoffeerd" in text_lower:
            data["furnished"] = "Upholstered"

        # Deposit
        deposit_match = re.search(r"deposit[:\s]*€?\s*([\d.,]+)", text_lower)
        if deposit_match:
            deposit_str = deposit_match.group(1).replace(".", "").replace(",", ".")
            try:
                data["deposit_eur"] = float(deposit_str)
            except ValueError:
                pass

        # Available date
        avail_patterns = [
            r"available\s*(?:from)?\s*:?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"available\s*(?:from)?\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})",
            r"available\s*(?:from)?\s*:?\s*(immediately|now|direct)",
        ]
        for pattern in avail_patterns:
            match = re.search(pattern, text_lower)
            if match:
                data["available_from"] = match.group(1)
                break

        # Pets/Smoking
        if "pets allowed" in text_lower or "huisdieren toegestaan" in text_lower:
            data["pets_allowed"] = True
        elif "no pets" in text_lower or "pets not allowed" in text_lower:
            data["pets_allowed"] = False

        if "smoking allowed" in text_lower:
            data["smoking_allowed"] = True
        elif "no smoking" in text_lower or "smoking not allowed" in text_lower:
            data["smoking_allowed"] = False

        # Energy label
        energy_match = re.search(r"energy\s*(?:label)?[:\s]*([A-G]\+*)", full_text, re.IGNORECASE)
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Description - try meta description or specific elements
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        # Agency
        agency_patterns = [
            r"offered\s*(?:by|through)[:\s]*([A-Za-z\s]+?)(?:\.|,|$)",
            r"agency[:\s]*([A-Za-z\s]+?)(?:\.|,|$)",
        ]
        for pattern in agency_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                agency = match.group(1).strip()
                if agency and len(agency) > 2:
                    data["agency"] = agency
                break

        return data
