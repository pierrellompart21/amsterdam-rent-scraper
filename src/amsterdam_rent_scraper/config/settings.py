"""Configuration for scraping targets and search parameters."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# === CITY CONFIGURATION ===
@dataclass
class CityConfig:
    """Configuration for a city."""

    name: str
    country: str
    work_address: str
    work_lat: float
    work_lng: float
    min_price: int
    max_price: int
    min_surface: Optional[int] = None
    min_rooms: Optional[int] = None
    currency: str = "EUR"
    # Map display settings
    map_center_lat: Optional[float] = None
    map_center_lng: Optional[float] = None
    map_default_zoom: int = 12
    # Transit routing API to use (transitous, hsl, etc.)
    transit_api: str = "transitous"
    # List of enabled scraper names for this city
    enabled_scrapers: list[str] = field(default_factory=list)


# City configurations
CITIES: dict[str, CityConfig] = {
    "amsterdam": CityConfig(
        name="Amsterdam",
        country="Netherlands",
        work_address="Stroombaan 4, 1181 VX Amstelveen, Netherlands",
        work_lat=52.3027,
        work_lng=4.8557,
        min_price=1000,
        max_price=2000,
        currency="EUR",
        map_center_lat=52.3676,
        map_center_lng=4.9041,
        map_default_zoom=12,
        transit_api="transitous",
        enabled_scrapers=[
            "pararius", "huurwoningen", "123wonen", "huurstunt",
            "kamernet", "iamexpat", "rotsvast", "expathousingnetwork", "huure"
        ],
    ),
    "helsinki": CityConfig(
        name="Helsinki",
        country="Finland",
        work_address="Keilasatama 5, 02150 Espoo, Finland",
        work_lat=60.1756,
        work_lng=24.8271,
        min_price=800,
        max_price=1800,
        min_surface=40,
        min_rooms=2,
        currency="EUR",
        map_center_lat=60.1699,
        map_center_lng=24.9384,
        map_default_zoom=11,
        transit_api="hsl",  # Helsinki Region Transport (HSL) Digitransit API
        enabled_scrapers=["sato", "oikotie", "lumo", "ta", "retta"],  # Finnish rental scrapers
    ),
}

# Default city
DEFAULT_CITY = "amsterdam"


def get_city_config(city: str = None) -> CityConfig:
    """Get configuration for a city."""
    city = (city or DEFAULT_CITY).lower()
    if city not in CITIES:
        raise ValueError(f"Unknown city: {city}. Available: {list(CITIES.keys())}")
    return CITIES[city]


# === LEGACY COMPATIBILITY (for existing code) ===
# These will be deprecated - use get_city_config() instead
_default_city = get_city_config(DEFAULT_CITY)
WORK_ADDRESS = _default_city.work_address
WORK_LAT = _default_city.work_lat
WORK_LNG = _default_city.work_lng
MIN_PRICE = _default_city.min_price
MAX_PRICE = _default_city.max_price
CURRENCY = _default_city.currency

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
    city: str = "amsterdam"  # Which city this site is for
    enabled: bool = True
    needs_js: bool = False  # requires Selenium/Playwright
    notes: str = ""


# === ALL RENTAL SITES ===
# Sites are organized by city
RENTAL_SITES: list[RentalSite] = [
    # =====================
    # AMSTERDAM (Netherlands)
    # =====================
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
    RentalSite(
        name="expathousingnetwork",
        base_url="https://expathousingnetwork.nl",
        search_url_template="https://expathousingnetwork.nl/listings-to-rent",
        scraper_class="amsterdam_rent_scraper.scrapers.expathousingnetwork.ExpatHousingNetworkScraper",
        needs_js=True,
        notes="Expat-focused housing agency. Webflow site with permissive robots.txt.",
    ),
    RentalSite(
        name="huure",
        base_url="https://huure.nl",
        search_url_template=(
            "https://huure.nl/apartments-for-rent/amsterdam"
            "?min_rent={min_price}&max_rent={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.huure.HuureScraper",
        needs_js=False,
        notes="Dutch rental aggregator with server-rendered content. Permissive robots.txt.",
    ),
    # =====================
    # HELSINKI (Finland)
    # =====================
    RentalSite(
        name="vuokraovi",
        base_url="https://www.vuokraovi.com",
        search_url_template=(
            "https://www.vuokraovi.com/vuokra-asunnot"
            "?locale=en&rentMin={min_price}&rentMax={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.vuokraovi.VuokraoviScraper",
        city="helsinki",
        enabled=False,  # Disabled: blocks headless browsers
        needs_js=True,
        notes="Major Finnish rental portal. Blocks headless browsers.",
    ),
    RentalSite(
        name="sato",
        base_url="https://www.sato.fi",
        search_url_template="https://www.sato.fi/vuokra-asunnot",
        scraper_class="amsterdam_rent_scraper.scrapers.sato.SatoScraper",
        city="helsinki",
        needs_js=True,
        notes="Major Finnish rental company. Next.js site, works with Playwright.",
    ),
    RentalSite(
        name="oikotie",
        base_url="https://asunnot.oikotie.fi",
        search_url_template="https://asunnot.oikotie.fi/vuokra-asunnot?pagination=1",
        scraper_class="amsterdam_rent_scraper.scrapers.oikotie.OikotieScraper",
        city="helsinki",
        needs_js=True,
        notes="Largest Finnish housing site. AngularJS, requires JS rendering.",
    ),
    RentalSite(
        name="lumo",
        base_url="https://lumo.fi",
        search_url_template="https://lumo.fi/vuokra-asunnot",
        scraper_class="amsterdam_rent_scraper.scrapers.lumo.LumoScraper",
        city="helsinki",
        needs_js=True,
        notes="Kojamo/Lumo rental apartments. React/Redux site, requires JS rendering.",
    ),
    RentalSite(
        name="ta",
        base_url="https://ta.fi",
        search_url_template="https://ta.fi/asunnot/vuokra-asunto/helsinki/",
        scraper_class="amsterdam_rent_scraper.scrapers.ta.TAScraper",
        city="helsinki",
        needs_js=True,
        notes="TA-Asunnot rental company. WordPress site with 5,000+ apartments.",
    ),
    RentalSite(
        name="retta",
        base_url="https://vuokraus.rettamanagement.fi",
        search_url_template="https://vuokraus.rettamanagement.fi/asunnot",
        scraper_class="amsterdam_rent_scraper.scrapers.retta.RettaScraper",
        city="helsinki",
        needs_js=True,
        notes="Retta Management rental apartments. Next.js site with JSON data in __NEXT_DATA__.",
    ),
    # Additional Helsinki sites to implement:
    # - etuovi.com (Finnish housing marketplace - redirects to vuokraovi for rentals)
    # - a-kruunu.fi (affordable rentals, uses Knockout.js - complex to scrape)
]


def get_enabled_sites(
    filter_names: list[str] | None = None, city: str = None
) -> list[RentalSite]:
    """Return enabled sites, optionally filtered by name and city."""
    city = (city or DEFAULT_CITY).lower()
    city_config = get_city_config(city)

    # Filter by city first
    sites = [s for s in RENTAL_SITES if s.city.lower() == city]

    # Then filter by enabled status (based on city config's enabled_scrapers list)
    if city_config.enabled_scrapers:
        enabled_names = {n.lower() for n in city_config.enabled_scrapers}
        sites = [s for s in sites if s.name.lower() in enabled_names]
    else:
        # If no explicit enabled list, use the site's own enabled flag
        sites = [s for s in sites if s.enabled]

    # Apply name filter if provided
    if filter_names:
        names = {n.lower() for n in filter_names}
        sites = [s for s in sites if s.name.lower() in names]

    return sites


def get_all_sites_for_city(city: str = None) -> list[RentalSite]:
    """Return all sites for a city (including disabled ones)."""
    city = (city or DEFAULT_CITY).lower()
    return [s for s in RENTAL_SITES if s.city.lower() == city]
