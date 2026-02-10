"""BostadsPortal.se scraper - Swedish rental marketplace (server-rendered)."""

import json
import re
from urllib.parse import urljoin, urlencode

from bs4 import BeautifulSoup
from playwright.sync_api import Page

from amsterdam_rent_scraper.scrapers.playwright_base import PlaywrightBaseScraper, console


class BostadsportalScraper(PlaywrightBaseScraper):
    """Scraper for bostadsportal.se Swedish rental listings.

    BostadsPortal is a Swedish rental marketplace with 10,000+ listings across Sweden.
    The site is server-rendered with React and uses JSON-LD structured data.

    URL patterns:
    - Search: https://www.bostadsportal.se/hyra-lägenhet/stockholm/
    - With filters: ?min_rooms=2&max_rent=25000&min_rent=10000
    - Listing: /hyra-lägenhet/stockholm/70m2-3-rok-id-6339305
    """

    site_name = "bostadsportal"
    base_url = "https://www.bostadsportal.se"

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
        """Build search URL for Stockholm area rentals with price filter."""
        # URL-encoded path for "hyra-lägenhet"
        base = f"{self.base_url}/hyra-l%C3%A4genhet/stockholm/"
        params = {}
        if self.min_price:
            params["min_rent"] = int(self.min_price)
        if self.max_price:
            params["max_rent"] = int(self.max_price)
        if page_num > 1:
            params["page"] = page_num
        if params:
            return f"{base}?{urlencode(params)}"
        return base

    def _handle_cookie_consent(self, page: Page):
        """Handle cookie consent dialogs."""
        try:
            consent_selectors = [
                'button:has-text("Acceptera")',
                'button:has-text("Accept")',
                'button:has-text("Godkänn")',
                'button:has-text("OK")',
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
        max_pages = 15  # Limit pagination

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

                # Find listing links - pattern: /hyra-lägenhet/stockholm/XXm2-Y-rok-id-ZZZZZ
                listing_links = soup.find_all("a", href=re.compile(r"/hyra-[^/]+/stockholm/.*-id-\d+"))

                if not listing_links:
                    console.print(f"  No listings found on page {current_page}")
                    break

                new_urls = 0
                for link in listing_links:
                    href = link.get("href", "")
                    # Extract ID to deduplicate
                    id_match = re.search(r"-id-(\d+)", href)
                    if id_match:
                        listing_id = id_match.group(1)
                        if listing_id not in seen_ids:
                            seen_ids.add(listing_id)
                            full_url = urljoin(self.base_url, href)
                            urls.append(full_url)
                            new_urls += 1

                console.print(f"  Page {current_page}: Found {new_urls} new listings")

                if new_urls == 0:
                    # No new listings found, stop pagination
                    break

                # Check for next page - look for pagination or "Nästa" button
                next_btn = soup.find("a", string=re.compile(r"Nästa|Next", re.IGNORECASE))
                next_page_link = soup.find("a", href=re.compile(rf"page={current_page + 1}"))

                if not next_btn and not next_page_link:
                    # Also check for numbered pagination buttons
                    page_links = soup.find_all("a", href=re.compile(r"page=\d+"))
                    has_next = any(f"page={current_page + 1}" in (a.get("href") or "") for a in page_links)
                    if not has_next:
                        break

                current_page += 1

            except Exception as e:
                console.print(f"  [red]Error on page {current_page}: {e}[/]")
                break

        console.print(f"  Total: Found {len(urls)} listing URLs")
        return urls[: self.max_listings] if self.max_listings else urls

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a BostadsPortal listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        full_text = soup.get_text(" ", strip=True)

        # Try JSON-LD structured data first (most reliable)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld_data = json.loads(script.string)
                items = ld_data if isinstance(ld_data, list) else [ld_data]
                for item in items:
                    if item.get("@type") == "RealEstateListing":
                        if item.get("name"):
                            data["title"] = item["name"]
                        if item.get("description"):
                            data["description"] = item["description"][:2000]
                        if item.get("url"):
                            data["canonical_url"] = item["url"]

                        # Address from structured data
                        if item.get("address"):
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

                        # Price from offer
                        if item.get("offers"):
                            offer = item["offers"]
                            if isinstance(offer, dict) and offer.get("price"):
                                try:
                                    price = float(offer["price"])
                                    if 1000 <= price <= 100000:
                                        data["price_sek"] = price
                                        data["price_eur"] = round(price / 11.5, 2)
                                except (ValueError, TypeError):
                                    pass

            except (json.JSONDecodeError, TypeError):
                continue

        # Extract from URL pattern: /70m2-3-rok-id-6339305
        url_match = re.search(r"/(\d+)m2-(\d+)-rok-id-(\d+)", url)
        if url_match:
            if "surface_m2" not in data:
                try:
                    data["surface_m2"] = float(url_match.group(1))
                except ValueError:
                    pass
            if "rooms" not in data:
                try:
                    data["rooms"] = int(url_match.group(2))
                except ValueError:
                    pass

        # Title from og:title or page title if not from JSON-LD
        if "title" not in data:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                data["title"] = og_title["content"]
            else:
                title_tag = soup.find("title")
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    title = re.sub(r"\s*[|\-]\s*BostadsPortal.*$", "", title, flags=re.IGNORECASE)
                    data["title"] = title

        # Price from HTML if not from JSON-LD
        if "price_sek" not in data:
            # Pattern: "16 123 kr" or "16123 kr"
            price_patterns = [
                r"(\d{1,3}(?:[\s\u00a0]\d{3})*)\s*kr\.?",  # 16 123 kr
                r"Månadshyra[:\s]*(\d{1,3}(?:[\s\u00a0]\d{3})*)",  # Månadshyra: 16 123
            ]
            for pattern in price_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    price_str = match.group(1).replace(" ", "").replace("\u00a0", "")
                    try:
                        price = float(price_str)
                        if 1000 <= price <= 100000:
                            data["price_sek"] = price
                            data["price_eur"] = round(price / 11.5, 2)
                            break
                    except ValueError:
                        continue

        # Surface area from HTML if not from URL
        if "surface_m2" not in data:
            surface_patterns = [
                r"(\d+(?:[.,]\d+)?)\s*m[²2]",
                r"(\d+(?:[.,]\d+)?)\s*kvm",
            ]
            for pattern in surface_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    try:
                        data["surface_m2"] = float(match.group(1).replace(",", "."))
                        break
                    except ValueError:
                        continue

        # Rooms from HTML if not from URL
        if "rooms" not in data:
            room_patterns = [
                r"(\d+)\s*rum\s*(?:lägenhet|och\s*kök)?",
                r"(\d+)\s*rok\b",
            ]
            for pattern in room_patterns:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    try:
                        data["rooms"] = int(match.group(1))
                        break
                    except ValueError:
                        continue

        # Address from HTML if not from JSON-LD
        if "address" not in data:
            # Look for address pattern in the page - format: "Streetname, XXX XX City, District"
            # First try to find in the og:description or structured content
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                desc_text = og_desc["content"]
                # Extract street name that appears before "det har" or similar
                addr_match = re.search(r"ligger\s+(?:på\s+)?([A-ZÄÖÅ][a-zäöåA-ZÄÖÅ\s]+?)(?:,|\.\s|det\s)", desc_text)
                if addr_match:
                    street = addr_match.group(1).strip()
                    if len(street) > 3 and len(street) < 50:
                        data["address"] = f"{street}, Stockholm"

            # Also look for postal code pattern in full text: "XXX XX City"
            if "address" not in data:
                postal_addr_match = re.search(r"(\d{3})\s*(\d{2})\s+(Stockholm|Solna|Sundbyberg|Nacka|Lidingö|Danderyd)", full_text, re.IGNORECASE)
                if postal_addr_match:
                    data["postal_code"] = f"{postal_addr_match.group(1)} {postal_addr_match.group(2)}"
                    city = postal_addr_match.group(3).title()
                    data["address"] = f"{data.get('postal_code', '')}, {city}".strip(", ")

        # Postal code from HTML if not from JSON-LD
        if "postal_code" not in data:
            # Swedish postal code: XXX XX or XXXXX
            postal_match = re.search(r"\b(\d{3})\s*(\d{2})\b", full_text)
            if postal_match:
                data["postal_code"] = f"{postal_match.group(1)} {postal_match.group(2)}"

        # Floor (våning in Swedish)
        floor_match = re.search(r"(\d+)(?::a|:e)?\s*våning(?:en)?", full_text, re.IGNORECASE)
        if floor_match:
            data["floor"] = floor_match.group(1)

        # Balcony
        if re.search(r"\bbalkong\b", full_text, re.IGNORECASE):
            data["has_balcony"] = True

        # Elevator (hiss)
        if re.search(r"\bhiss\b", full_text, re.IGNORECASE):
            data["has_elevator"] = True

        # Furnished (möblerad)
        if re.search(r"\bmöbler(?:ad|at)\b", full_text, re.IGNORECASE):
            data["is_furnished"] = True

        # Parking
        if re.search(r"\b(?:parkering|garage)\b", full_text, re.IGNORECASE):
            data["has_parking"] = True

        # Description from meta if not from JSON-LD
        if "description" not in data:
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                data["description"] = meta_desc["content"][:2000]

        data["property_type"] = "Apartment"
        return data
