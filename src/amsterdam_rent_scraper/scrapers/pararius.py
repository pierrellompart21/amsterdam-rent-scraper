"""Pararius.com scraper - relatively scraper-friendly Dutch rental site."""

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from amsterdam_rent_scraper.scrapers.base import BaseScraper, console


class ParariusScraper(BaseScraper):
    """Scraper for pararius.com rental listings."""

    site_name = "pararius"
    base_url = "https://www.pararius.com"

    def get_search_url(self, page: int = 1) -> str:
        """Build search URL for given page."""
        base = f"{self.base_url}/apartments/amsterdam/{self.min_price}-{self.max_price}"
        if page > 1:
            return f"{base}/page-{page}"
        return base

    def get_listing_urls(self) -> list[str]:
        """Scrape search results to get all listing URLs."""
        urls = []
        page = 1
        max_pages = 2 if self.test_mode else 50

        while page <= max_pages:
            search_url = self.get_search_url(page)
            console.print(f"  Fetching search page {page}: {search_url}")

            try:
                html = self.fetch_page(search_url)
                soup = BeautifulSoup(html, "lxml")

                # Find listing links - Pararius uses .listing-search-item__link
                listing_links = soup.select("a.listing-search-item__link")

                if not listing_links:
                    # Try alternative selectors
                    listing_links = soup.select(
                        'a[href*="/apartment-for-rent/amsterdam/"]'
                    )

                if not listing_links:
                    console.print(f"  No more listings found on page {page}")
                    break

                for link in listing_links:
                    href = link.get("href", "")
                    if href and "/apartment-for-rent/" in href:
                        full_url = urljoin(self.base_url, href)
                        if full_url not in urls:
                            urls.append(full_url)

                console.print(f"  Page {page}: found {len(listing_links)} links")

                # Check if there's a next page
                next_btn = soup.select_one('a[rel="next"]') or soup.select_one(
                    ".pagination__link--next"
                )
                if not next_btn:
                    break

                page += 1
                self._delay()

            except Exception as e:
                console.print(f"  [red]Error on page {page}: {e}[/]")
                break

        return urls[: self.max_listings]

    def parse_listing_page(self, html: str, url: str) -> dict:
        """Parse a Pararius listing page and extract data."""
        soup = BeautifulSoup(html, "lxml")
        data = {}

        # Title
        title_el = soup.select_one("h1.listing-detail-summary__title")
        if title_el:
            data["title"] = title_el.get_text(strip=True)

        # Price
        price_el = soup.select_one(".listing-detail-summary__price")
        if price_el:
            price_text = price_el.get_text(strip=True)
            # Extract number from "€1,500 per month"
            price_match = re.search(r"[\d,.]+", price_text.replace(",", ""))
            if price_match:
                try:
                    data["price_eur"] = float(price_match.group().replace(".", ""))
                except ValueError:
                    pass

        # Address
        address_el = soup.select_one(".listing-detail-summary__location")
        if address_el:
            data["address"] = address_el.get_text(strip=True)

        # Features section - contains many details
        features = soup.select(".listing-features__main-description li")
        for feature in features:
            text = feature.get_text(strip=True).lower()

            # Surface area
            if "m²" in text or "m2" in text:
                match = re.search(r"(\d+)\s*m", text)
                if match:
                    data["surface_m2"] = float(match.group(1))

            # Rooms
            if "room" in text:
                match = re.search(r"(\d+)", text)
                if match:
                    data["rooms"] = int(match.group(1))

            # Furnished status
            if "furnished" in text:
                if "unfurnished" in text:
                    data["furnished"] = "Unfurnished"
                elif "upholstered" in text:
                    data["furnished"] = "Upholstered"
                else:
                    data["furnished"] = "Furnished"

        # More detailed features from the details table
        detail_items = soup.select(".listing-features__term, .listing-features__description")
        current_term = None
        for item in detail_items:
            if "term" in item.get("class", []):
                current_term = item.get_text(strip=True).lower()
            elif current_term:
                value = item.get_text(strip=True)
                if "bedroom" in current_term:
                    match = re.search(r"(\d+)", value)
                    if match:
                        data["bedrooms"] = int(match.group(1))
                elif "bathroom" in current_term:
                    match = re.search(r"(\d+)", value)
                    if match:
                        data["bathrooms"] = int(match.group(1))
                elif "available" in current_term:
                    data["available_date"] = value
                elif "deposit" in current_term:
                    match = re.search(r"[\d,.]+", value.replace(",", ""))
                    if match:
                        try:
                            data["deposit_eur"] = float(match.group().replace(".", ""))
                        except ValueError:
                            pass
                elif "energy" in current_term:
                    data["energy_label"] = value
                elif "floor" in current_term or "storey" in current_term:
                    data["floor"] = value
                current_term = None

        # Description
        desc_el = soup.select_one(".listing-detail-description__content")
        if desc_el:
            data["description"] = desc_el.get_text(strip=True)[:2000]

        # Agent/Landlord
        agent_el = soup.select_one(".agent-summary__title-link")
        if agent_el:
            data["agency"] = agent_el.get_text(strip=True)

        # Postal code from address
        if "address" in data:
            postal_match = re.search(r"\b(\d{4}\s?[A-Z]{2})\b", data["address"])
            if postal_match:
                data["postal_code"] = postal_match.group(1).replace(" ", "")

        return data
