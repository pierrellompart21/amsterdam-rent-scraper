"""Expat Housing Network scraper - Webflow-based site with permissive robots.txt."""

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class ExpatHousingNetworkScraper(PlaywrightBaseScraper):
    """Scraper for expathousingnetwork.nl rental listings (Webflow, needs JS)."""

    site_name = "expathousingnetwork"
    base_url = "https://expathousingnetwork.nl"

    def fetch_page(self, url: str, page=None, wait_selector: str | None = None) -> str:
        """Fetch a page with JavaScript rendering - optimized for Webflow sites."""
        close_page = page is None
        if page is None:
            page = self._new_page()

        try:
            # Webflow sites load content dynamically
            page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for content to appear
            try:
                page.wait_for_selector("h1, [class*='price'], [class*='rent']", timeout=10000)
            except Exception:
                pass

            # Small delay for dynamic content
            page.wait_for_timeout(2000)

            return page.content()
        finally:
            if close_page:
                page.close()

    def get_listing_urls(self, page: Page) -> list[str]:
        """Scrape the listings page to get all rental property URLs."""
        urls = []
        search_url = f"{self.base_url}/listings-to-rent"

        console.print(f"  Fetching listings page: {search_url}")

        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # Wait for listing links
            try:
                page.wait_for_selector('a[href*="/property/"]', timeout=15000)
            except Exception:
                console.print("  [yellow]No property links found on initial load[/]")

            # Scroll to load all content (Webflow may lazy-load)
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(1500)

            html = page.content()
            soup = BeautifulSoup(html, "lxml")

            # Find all property links
            for link in soup.select('a[href*="/property/"]'):
                href = link.get("href", "")
                # Exclude any non-listing paths
                if "/property/" in href and not href.endswith("/property/"):
                    full_url = urljoin(self.base_url, href)
                    if full_url not in urls:
                        urls.append(full_url)

            console.print(f"  Found {len(urls)} listing URLs")

        except Exception as e:
            console.print(f"  [red]Error fetching listings: {e}[/]")

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse an Expat Housing Network listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Try JSON-LD structured data
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    if item.get("@type") in ["Product", "Apartment", "House", "RealEstateListing", "SingleFamilyResidence"]:
                        if "name" in item:
                            data["title"] = item["name"]
                        if "description" in item:
                            data["description"] = item["description"][:2000]
                        if "offers" in item:
                            offers = item["offers"]
                            if isinstance(offers, dict) and "price" in offers:
                                try:
                                    data["price_eur"] = float(offers["price"])
                                except (ValueError, TypeError):
                                    pass
                        if "address" in item:
                            addr = item["address"]
                            if isinstance(addr, dict):
                                parts = []
                                if addr.get("streetAddress"):
                                    parts.append(addr["streetAddress"])
                                if addr.get("postalCode"):
                                    data["postal_code"] = addr["postalCode"]
                                if addr.get("addressLocality"):
                                    parts.append(addr["addressLocality"])
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

        # Address from URL slug as fallback
        # URL pattern: /property/street-name-city
        if "address" not in data:
            url_match = re.search(r"/property/([a-z\-]+)/?$", url, re.IGNORECASE)
            if url_match:
                addr_slug = url_match.group(1)
                # Convert slug to readable address
                addr_parts = addr_slug.replace("-", " ").title()
                data["address"] = addr_parts

        # Price extraction
        if "price_eur" not in data:
            price_patterns = [
                r"€\s*([\d.,]+)\s*(?:/month|per\s*month|p\.?m\.?|monthly)?",
                r"([\d.,]+)\s*€\s*(?:/month|per\s*month)?",
                r"rent[:\s]*€?\s*([\d.,]+)",
            ]
            for pattern in price_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(".", "").replace(",", ".")
                    price_str = price_str.rstrip(".")
                    try:
                        price = float(price_str)
                        if 100 <= price <= 20000:
                            data["price_eur"] = price
                            break
                    except ValueError:
                        continue

        # Surface area - look for m² or m2
        surface_patterns = [
            r"(\d+)\s*m[²2]",
            r"size[:\s]*(\d+)",
            r"(\d+)\s*square\s*m",
        ]
        for pattern in surface_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                surface = int(match.group(1))
                if 10 <= surface <= 1000:
                    data["surface_m2"] = float(surface)
                    break

        # Rooms
        rooms_patterns = [
            r"(\d+)\s*(?:room|kamer)(?:s)?\b",
            r"rooms?[:\s]*(\d+)",
        ]
        for pattern in rooms_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                rooms = int(match.group(1))
                if 1 <= rooms <= 20:
                    data["rooms"] = rooms
                    break

        # Bedrooms
        bedroom_patterns = [
            r"(\d+)\s*(?:bedroom|slaapkamer)(?:s)?",
            r"bedroom(?:s)?[:\s]*(\d+)",
        ]
        for pattern in bedroom_patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                bedrooms = int(match.group(1))
                if 1 <= bedrooms <= 10:
                    data["bedrooms"] = bedrooms
                    break

        # Bathrooms
        bath_match = re.search(r"(\d+)\s*(?:bathroom|badkamer)(?:s)?", full_text, re.IGNORECASE)
        if bath_match:
            data["bathrooms"] = int(bath_match.group(1))

        # Postal code - Dutch format: 1234AB
        postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", full_text)
        if postal_match and "postal_code" not in data:
            data["postal_code"] = postal_match.group(1).replace(" ", "")

        # Property type
        text_lower = full_text.lower()
        if "apartment" in text_lower or "appartement" in text_lower:
            data["property_type"] = "Apartment"
        elif "house" in text_lower or "huis" in text_lower or "woning" in text_lower:
            data["property_type"] = "House"
        elif "studio" in text_lower:
            data["property_type"] = "Studio"
        elif "room" in text_lower or "kamer" in text_lower:
            data["property_type"] = "Room"

        # Furnished status
        if "furnished" in text_lower:
            if "unfurnished" in text_lower:
                data["furnished"] = "Unfurnished"
            elif "semi-furnished" in text_lower or "semi furnished" in text_lower:
                data["furnished"] = "Semi-Furnished"
            else:
                data["furnished"] = "Furnished"
        elif "gemeubileerd" in text_lower:
            data["furnished"] = "Furnished"
        elif "gestoffeerd" in text_lower:
            data["furnished"] = "Upholstered"

        # Available date
        avail_patterns = [
            r"available\s*(?:from|starting)?[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
            r"available\s*(?:from|starting)?[:\s]*(\w+\s+\d{1,2},?\s+\d{4})",
            r"available\s*(?:from|starting)?[:\s]*(immediately|now|direct)",
            r"beschikbaar\s*(?:per|vanaf)?[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        ]
        for pattern in avail_patterns:
            match = re.search(pattern, text_lower)
            if match:
                data["available_from"] = match.group(1)
                break

        # Deposit
        deposit_match = re.search(
            r"deposit[:\s]*€?\s*([\d.,]+)",
            text_lower
        )
        if deposit_match:
            deposit_str = deposit_match.group(1).replace(".", "").replace(",", ".")
            try:
                deposit = float(deposit_str)
                if 100 <= deposit <= 50000:
                    data["deposit_eur"] = deposit
            except ValueError:
                pass

        # Energy label
        energy_match = re.search(
            r"energy\s*(?:label)?[:\s]*([A-G]\+*)",
            full_text,
            re.IGNORECASE
        )
        if energy_match:
            data["energy_label"] = energy_match.group(1).upper()

        # Description
        if "description" not in data:
            desc_el = soup.select_one('meta[name="description"]')
            if desc_el and desc_el.get("content"):
                data["description"] = desc_el["content"][:2000]

        # Agency - this site is the agency
        data["agency"] = "Expat Housing Network"

        return data
