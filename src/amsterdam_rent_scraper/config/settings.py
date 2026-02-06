"""Configuration for scraping targets and search parameters."""

from dataclasses import dataclass
from pathlib import Path


# === WORK LOCATION ===
WORK_ADDRESS = "Stroombaan 4, 1181 VX Amstelveen, Netherlands"
WORK_LAT = 52.3027  # Corrected coordinates for Stroombaan 4
WORK_LNG = 4.8557

# === SEARCH PARAMETERS ===
MIN_PRICE = 1000
MAX_PRICE = 2000
CURRENCY = "EUR"

# === SCRAPING CONFIG ===
REQUEST_DELAY_MIN = 2.0  # seconds
REQUEST_DELAY_MAX = 5.0
MAX_RETRIES = 3
TIMEOUT = 30

# === LLM CONFIG ===
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"  # or "llama3.1:8b", "mistral" — pick what you have loaded
LLM_TIMEOUT = 120
LLM_MAX_INPUT_CHARS = 12000  # truncate page content to fit context

# === OUTPUT ===
OUTPUT_DIR = Path("output")
EXCEL_FILENAME = "amsterdam_rentals.xlsx"
HTML_FILENAME = "amsterdam_rentals.html"
RAW_PAGES_DIR = OUTPUT_DIR / "raw_pages"
DATABASE_PATH = OUTPUT_DIR / "listings.db"


@dataclass
class RentalSite:
    """A rental website to scrape."""

    name: str
    base_url: str
    search_url_template: str
    scraper_class: str  # dotted path to scraper class
    enabled: bool = True
    needs_js: bool = False  # requires Selenium/Playwright
    notes: str = ""


# === ALL DUTCH RENTAL SITES ===
RENTAL_SITES: list[RentalSite] = [
    RentalSite(
        name="funda",
        base_url="https://www.funda.nl",
        search_url_template=(
            "https://www.funda.nl/huur/amsterdam/beschikbaar/"
            "{min_price}-{max_price}/"
            "?selected_area=%5B%22amsterdam%22,%22amstelveen%22,"
            "%22diemen%22,%22ouderkerk-aan-de-amstel%22,%22badhoevedorp%22%5D"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.funda.FundaScraper",
        enabled=False,  # Disabled: aggressive anti-bot blocks headless browsers
        needs_js=True,
        notes="Largest Dutch housing site. Aggressive anti-bot blocks headless browsers.",
    ),
    RentalSite(
        name="pararius",
        base_url="https://www.pararius.com",
        search_url_template=(
            "https://www.pararius.com/apartments/amsterdam/" "{min_price}-{max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.pararius.ParariusScraper",
        needs_js=False,
        notes="Good HTML structure, relatively scraper-friendly.",
    ),
    RentalSite(
        name="kamernet",
        base_url="https://kamernet.nl",
        search_url_template=(
            "https://kamernet.nl/huren/huurwoningen-amsterdam"
            "?minRent={min_price}&maxRent={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.kamernet.KamernetScraper",
        needs_js=True,
    ),
    RentalSite(
        name="huurwoningen",
        base_url="https://www.huurwoningen.nl",
        search_url_template=(
            "https://www.huurwoningen.nl/in/amsterdam/" "?price={min_price}-{max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.huurwoningen.HuurwoningenScraper",
        needs_js=False,
    ),
    RentalSite(
        name="rentslam",
        base_url="https://rentslam.com",
        search_url_template="https://rentslam.com/en/apartments/amsterdam",
        scraper_class="amsterdam_rent_scraper.scrapers.rentslam.RentslamScraper",
        enabled=False,  # Disabled: not loading individual listings properly
        needs_js=True,
        notes="Aggregator. Not loading listings properly in headless mode.",
    ),
    RentalSite(
        name="housinganywhere",
        base_url="https://housinganywhere.com",
        search_url_template=(
            "https://housinganywhere.com/s/Amsterdam--Netherlands/"
            "apartment?priceMin={min_price}&priceMax={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.housinganywhere.HousingAnywhereScraper",
        enabled=False,  # Disabled: blocking headless browsers
        needs_js=True,
        notes="Blocks headless browsers - doesn't load listings.",
    ),
    RentalSite(
        name="directwonen",
        base_url="https://directwonen.nl",
        search_url_template="https://directwonen.nl/huurwoningen-huren/amsterdam",
        scraper_class="amsterdam_rent_scraper.scrapers.directwonen.DirectWonenScraper",
        enabled=False,  # Disabled: requires login/subscription to see prices and details
        needs_js=True,
        notes="Requires login/subscription to see prices and listing details.",
    ),
    RentalSite(
        name="huurstunt",
        base_url="https://www.huurstunt.nl",
        search_url_template="https://www.huurstunt.nl/huren/amsterdam/",
        scraper_class="amsterdam_rent_scraper.scrapers.huurstunt.HuurstuntScraper",
        needs_js=True,
        notes="Listings load dynamically. No URL price filtering available.",
    ),
    RentalSite(
        name="roofz",
        base_url="https://roofz.nl",
        search_url_template="https://roofz.nl/en/rent/amsterdam",
        scraper_class="amsterdam_rent_scraper.scrapers.roofz.RoofzScraper",
        enabled=False,  # Disabled: site timing out / not responding
        needs_js=True,
        notes="Site often times out or not responding.",
    ),
    RentalSite(
        name="123wonen",
        base_url="https://www.123wonen.nl",
        search_url_template=(
            "https://www.123wonen.nl/huurwoningen/in/amsterdam"
            "?maxprice={max_price}&minprice={min_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.wonen123.Wonen123Scraper",
        needs_js=False,
    ),
    RentalSite(
        name="iamexpat",
        base_url="https://www.iamexpat.nl",
        search_url_template=(
            "https://www.iamexpat.nl/housing/rentals/amsterdam"
            "?minPrice={min_price}&maxPrice={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.iamexpat.IamExpatScraper",
        needs_js=True,
        notes="Expat-focused housing platform. Next.js site requires Playwright.",
    ),
    RentalSite(
        name="rotsvast",
        base_url="https://www.rotsvast.nl",
        search_url_template="https://www.rotsvast.nl/huren/amsterdam/",
        scraper_class="amsterdam_rent_scraper.scrapers.rotsvast.RotsvastScraper",
        needs_js=False,
        notes="Dutch rental agency with permissive robots.txt.",
    ),
]


def get_enabled_sites(filter_names: list[str] | None = None) -> list[RentalSite]:
    """Return enabled sites, optionally filtered by name."""
    sites = [s for s in RENTAL_SITES if s.enabled]
    if filter_names:
        names = {n.lower() for n in filter_names}
        sites = [s for s in sites if s.name.lower() in names]
    return sites
