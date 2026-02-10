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
        min_price=1000,
        max_price=2000,
        min_surface=40,
        min_rooms=2,
        currency="EUR",
        map_center_lat=60.1699,
        map_center_lng=24.9384,
        map_default_zoom=11,
        transit_api="hsl",  # Helsinki Region Transport (HSL) Digitransit API
        enabled_scrapers=["sato", "oikotie", "lumo", "ta", "retta", "avara", "keva", "ovv"],  # Finnish rental scrapers
    ),
    "stockholm": CityConfig(
        name="Stockholm",
        country="Sweden",
        work_address="Vasagatan 12, 111 20 Stockholm, Sweden",
        work_lat=59.3320,
        work_lng=18.0590,
        min_price=11500,  # ~1000 EUR in SEK
        max_price=23000,  # ~2000 EUR in SEK
        min_surface=40,
        min_rooms=2,
        currency="SEK",
        map_center_lat=59.3293,
        map_center_lng=18.0686,
        map_default_zoom=11,
        transit_api="transitous",  # Transitous works for Sweden
        enabled_scrapers=[
            "blocket", "qasa", "samtrygg", "homeq", "bostadsportalen",
            "hyresbostad", "bovision", "bostad_direkt", "hemavi", "renthia",
            "heimstaden"
        ],
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

# === STEALTH MODE CONFIG ===
# Sites that have stealth scrapers available (only used with --stealth flag)
# These sites block standard headless browsers and need special handling
STEALTH_SITES = {
    "funda": {
        "stealth_class": "amsterdam_rent_scraper.scrapers.funda_stealth.FundaStealthScraper",
        "city": "amsterdam",
        "notes": "Aggressive anti-bot, requires undetected-chromedriver",
    },
    "vuokraovi": {
        "stealth_class": "amsterdam_rent_scraper.scrapers.vuokraovi_stealth.VuokraoviStealthScraper",
        "city": "helsinki",
        "notes": "Blocks headless browsers, requires undetected-chromedriver",
    },
}

# Stealth-specific delay settings (more conservative)
STEALTH_DELAY_MIN = 4.0  # seconds
STEALTH_DELAY_MAX = 8.0

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
    RentalSite(
        name="avara",
        base_url="https://www.avara.fi",
        search_url_template="https://oma.avara.fi/api/apartments/free?locations=helsinki,espoo,vantaa",
        scraper_class="amsterdam_rent_scraper.scrapers.avara.AvaraScraper",
        city="helsinki",
        needs_js=False,  # Uses JSON API
        notes="Finnish rental company with ~7,000 apartments. Public JSON API.",
    ),
    RentalSite(
        name="keva",
        base_url="https://vuokra-asunnot.keva.fi",
        search_url_template="https://vuokra-asunnot.keva.fi/",
        scraper_class="amsterdam_rent_scraper.scrapers.keva.KevaScraper",
        city="helsinki",
        needs_js=False,  # Server-rendered WordPress site
        notes="Keva pension fund rental apartments (~3,500 units). WordPress site with clean HTML.",
    ),
    RentalSite(
        name="ovv",
        base_url="https://www.ovv.com",
        search_url_template="https://www.ovv.com/en/for-rent/?cities=Helsinki%20Auroranlinna",
        scraper_class="amsterdam_rent_scraper.scrapers.ovv.OVVScraper",
        city="helsinki",
        needs_js=True,
        notes="OVV Asuntopalvelut - manages Auroranlinna (City of Helsinki) ~6,000 apartments. WordPress AJAX + API interception.",
    ),
    # Additional Helsinki sites to implement:
    # - etuovi.com (Finnish housing marketplace - redirects to vuokraovi for rentals)
    # - a-kruunu.fi (affordable rentals, uses Knockout.js - complex to scrape)
    # =====================
    # STOCKHOLM (Sweden)
    # =====================
    RentalSite(
        name="blocket",
        base_url="https://www.blocket.se",
        search_url_template=(
            "https://www.blocket.se/annonser/stockholm/bostad/lagenheter"
            "?cg=3020&r=11&f=p&f=c&ps={min_price}&pe={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.blocket.BlocketScraper",
        city="stockholm",
        needs_js=True,
        notes="Sweden's largest classifieds site with huge rental section.",
    ),
    RentalSite(
        name="qasa",
        base_url="https://qasa.se",
        search_url_template=(
            "https://qasa.se/hyra/bostad/stockholm"
            "?minMonthlyCost={min_price}&maxMonthlyCost={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.qasa.QasaScraper",
        city="stockholm",
        needs_js=True,
        notes="Modern rental platform with tenant verification.",
    ),
    RentalSite(
        name="samtrygg",
        base_url="https://www.samtrygg.se",
        search_url_template=(
            "https://www.samtrygg.se/hyra-ut-bostad/lediga-bostader"
            "?region=stockholm"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.samtrygg.SamtryggScraper",
        city="stockholm",
        needs_js=True,
        notes="Rental platform with tenant insurance focus.",
    ),
    RentalSite(
        name="homeq",
        base_url="https://www.homeq.se",
        search_url_template=(
            "https://www.homeq.se/sok-bostad?area=stockholm"
            "&minRent={min_price}&maxRent={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.homeq.HomeQScraper",
        city="stockholm",
        needs_js=True,
        notes="Digital rental platform with verified landlords.",
    ),
    RentalSite(
        name="bostadsportalen",
        base_url="https://www.bostadsportalen.se",
        search_url_template=(
            "https://www.bostadsportalen.se/hyresratter/stockholm"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.bostadsportalen.BostadsportalenScraper",
        city="stockholm",
        needs_js=True,
        notes="Rental listings aggregator for Stockholm.",
    ),
    RentalSite(
        name="hyresbostad",
        base_url="https://www.hyresbostad.se",
        search_url_template=(
            "https://www.hyresbostad.se/lediga-lagenheter/stockholm"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.hyresbostad.HyresbostandScraper",
        city="stockholm",
        needs_js=True,
        notes="Swedish rental apartment listings.",
    ),
    RentalSite(
        name="bovision",
        base_url="https://www.bovision.se",
        search_url_template=(
            "https://www.bovision.se/hyra/lagenhet/stockholms-lan"
            "?minMonthlyRent={min_price}&maxMonthlyRent={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.bovision.BovisionScraper",
        city="stockholm",
        needs_js=True,
        notes="Swedish property portal with rental section.",
    ),
    RentalSite(
        name="bostad_direkt",
        base_url="https://www.bostaddirekt.com",
        search_url_template=(
            "https://www.bostaddirekt.com/hyra-lagenhet/stockholm"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.bostad_direkt.BostadDirektScraper",
        city="stockholm",
        needs_js=True,
        notes="Direct rental listings from landlords.",
    ),
    RentalSite(
        name="hemavi",
        base_url="https://hemavi.com",
        search_url_template=(
            "https://hemavi.com/sok?location=stockholm&type=hyresratt"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.hemavi.HemaviScraper",
        city="stockholm",
        needs_js=True,
        notes="Modern rental marketplace.",
    ),
    RentalSite(
        name="renthia",
        base_url="https://renthia.com",
        search_url_template=(
            "https://renthia.com/en/for-rent/stockholm"
            "?minPrice={min_price}&maxPrice={max_price}"
        ),
        scraper_class="amsterdam_rent_scraper.scrapers.renthia.RenthiaScraper",
        city="stockholm",
        needs_js=True,
        notes="International-friendly rental platform with English support.",
    ),
    RentalSite(
        name="heimstaden",
        base_url="https://mitt.heimstaden.com",
        search_url_template="https://mitt.heimstaden.com/ledigt/lagenhet",
        scraper_class="amsterdam_rent_scraper.scrapers.heimstaden.HeimstadenScraper",
        city="stockholm",
        needs_js=True,
        notes="Major Swedish rental company with apartments in Stockholm and other cities. Vue.js site.",
    ),
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


# === STOCKHOLM AREA LOCATIONS ===
# Cities/municipalities within 20km radius of Vasagatan 12, Stockholm
STOCKHOLM_AREA_LOCATIONS = [
    "stockholm",
    "solna",
    "sundbyberg",
    "nacka",
    "lidingö",
    "danderyd",
    "järfälla",
    "sollentuna",
    "huddinge",
    "bromma",
    "täby",
    "upplands väsby",
]

# Approximate coordinates for Stockholm area location centers
STOCKHOLM_LOCATION_CENTERS = {
    "stockholm": (59.3293, 18.0686),
    "solna": (59.3600, 18.0005),
    "sundbyberg": (59.3607, 17.9720),
    "nacka": (59.3106, 18.1631),
    "lidingö": (59.3633, 18.1381),
    "danderyd": (59.3997, 18.0284),
    "järfälla": (59.4280, 17.8350),
    "sollentuna": (59.4282, 17.9509),
    "huddinge": (59.2370, 17.9816),
    "bromma": (59.3380, 17.9426),
    "täby": (59.4437, 18.0685),
    "upplands väsby": (59.5185, 17.9138),
}
