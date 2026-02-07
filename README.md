# Multi-City Rent Scraper

A CLI tool to scrape rental listings from housing websites in **Amsterdam** and **Helsinki**, calculate commute times, analyze neighborhoods, and export to interactive HTML reports with maps.

## Features

- **Multi-city support** - Amsterdam (Netherlands) and Helsinki (Finland)
- **Multi-site scraping** - 9 Amsterdam sites + 8 Helsinki sites
- **Commute calculation** - Real bike/driving times via OSRM, transit via HSL Digitransit (Helsinki)
- **Neighborhood scoring** - Safety, amenities, green space, restaurants, expat-friendliness (1-10)
- **SQLite database** - City-specific persistent storage with deduplication
- **Interactive HTML report** - Cards/table views, map with route polylines, price slider
- **Excel export** - Full data export with all fields
- **CLI filters** - Price range, surface area, rooms, neighborhood scores

## Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/amsterdam-rent-scraper.git
cd amsterdam-rent-scraper

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .

# Install Playwright browsers (required for some sites)
playwright install chromium
```

## Quick Start

### Amsterdam (default)

```bash
# Test run - 3 listings per site, skip LLM extraction
rent-scraper scrape --test-run --sites pararius --skip-llm

# Scrape with filters
rent-scraper scrape --sites pararius,huurwoningen --skip-llm --min-surface 60 --min-rooms 2

# Full run - scrape all listings from enabled sites
rent-scraper scrape --skip-llm

# Export from database without re-scraping
rent-scraper export --format html --min-price 1200 --max-price 1800

# Check database statistics
rent-scraper db-info
```

### Helsinki

```bash
# Helsinki with all working scrapers
rent-scraper scrape --city helsinki --skip-llm

# Helsinki with specific scrapers
rent-scraper scrape --city helsinki --sites sato,lumo,avara --skip-llm

# Helsinki with limits
rent-scraper scrape --city helsinki --max-listings 20 --skip-llm

# Helsinki database info
rent-scraper db-info --city helsinki

# Helsinki export only
rent-scraper export --city helsinki --format html
```

## CLI Commands

### `rent-scraper scrape`

Scrape rental websites and save to database.

| Option | Description | Default |
|--------|-------------|---------|
| `--city, -c` | City to scrape: amsterdam, helsinki | amsterdam |
| `--test-run, -t` | Scrape only 3 listings per site | False |
| `--sites, -s` | Filter sites (comma-separated) | All enabled |
| `--max-listings, -n` | Max listings per site | Unlimited |
| `--min-price` | Minimum rent in EUR | City default |
| `--max-price` | Maximum rent in EUR | City default |
| `--min-surface` | Minimum surface area in m² | City default |
| `--min-rooms` | Minimum number of rooms | City default |
| `--apartments-only, -a` | Filter out rooms/shared housing | False |
| `--skip-llm` | Skip LLM extraction (regex only) | False |
| `--output-dir, -o` | Output directory | `./output` |

### `rent-scraper export`

Export listings from database to HTML/Excel.

| Option | Description | Default |
|--------|-------------|---------|
| `--format, -f` | Export format: excel, html, both | both |
| `--source, -s` | Filter by source site | None |
| `--min-price` | Minimum rent filter | None |
| `--max-price` | Maximum rent filter | None |
| `--min-surface` | Minimum surface area | None |
| `--min-rooms` | Minimum rooms | None |
| `--min-score` | Minimum neighborhood score | None |
| `--db, -d` | Database path | `output/listings.db` |

### `rent-scraper db-info`

Show database statistics.

## Architecture

```
src/amsterdam_rent_scraper/
├── cli/
│   └── main.py          # Typer CLI with scrape, export, db-info commands
├── config/
│   └── settings.py      # Site configs, work location, price ranges
├── scrapers/
│   ├── base.py          # BaseScraper with httpx
│   ├── playwright_base.py # PlaywrightScraper for JS-heavy sites
│   ├── pararius.py      # Pararius scraper (HTML)
│   ├── huurwoningen.py  # Huurwoningen scraper (JSON-LD)
│   ├── wonen123.py      # 123Wonen scraper (JSON-LD + HTML)
│   ├── huurstunt.py     # Huurstunt scraper (Playwright)
│   ├── kamernet.py      # Kamernet scraper (Playwright)
│   └── iamexpat.py      # IamExpat scraper (Playwright)
├── models/
│   └── listing.py       # RentalListing Pydantic model
├── llm/
│   ├── extractor.py     # Ollama LLM extraction
│   └── regex_fallback.py # Regex extraction fallback
├── storage/
│   └── database.py      # SQLite with deduplication
├── utils/
│   ├── geo.py           # OSRM routing, geocoding, commute times
│   └── neighborhoods.py # Neighborhood detection and scoring
├── export/
│   ├── html_report.py   # Interactive HTML with Leaflet maps
│   └── excel.py         # Excel export with openpyxl
└── pipeline.py          # Main orchestration with Rich progress
```

## Output

### Database

Listings are stored in city-specific SQLite databases:
- `output/amsterdam_listings.db` - Amsterdam listings
- `output/helsinki_listings.db` - Helsinki listings

Each database:
- Deduplicates by URL
- Stores all listing fields including commute times and neighborhood scores
- Supports filtered queries for export

### HTML Report

Interactive reports are generated per city:
- `output/amsterdam_rentals.html`
- `output/helsinki_rentals.html`

Features:
- **Cards view** - Visual cards with key info and neighborhood badges
- **Table view** - Sortable table with all fields
- **Map view** - Leaflet map with colored markers (green=cheap, yellow=mid, red=expensive)
- **Filters** - Price slider, surface/rooms/commute filters
- **Route display** - Click marker to show bike route to work

### Excel

Full data export per city:
- `output/amsterdam_rentals.xlsx`
- `output/helsinki_rentals.xlsx`

## Scraped Sites

### Amsterdam Sites

| Site | Status | Method | Notes |
|------|--------|--------|-------|
| pararius.com | Enabled | HTML | Reliable, good structure |
| huurwoningen.nl | Enabled | HTML/JSON-LD | Structured data |
| 123wonen.nl | Enabled | HTML/JSON-LD | Good fallback extraction |
| huurstunt.nl | Enabled | Playwright | Dynamic content |
| kamernet.nl | Enabled | Playwright | Rooms and apartments |
| iamexpat.nl | Enabled | Playwright | Expat-focused, Next.js |
| rotsvast.nl | Enabled | HTML | Dutch rental agency |
| funda.nl | Disabled | - | Aggressive anti-bot |
| housinganywhere.com | Disabled | - | Blocks headless browsers |
| directwonen.nl | Disabled | - | Requires subscription |

### Helsinki Sites

| Site | Status | Method | Notes |
|------|--------|--------|-------|
| sato.fi | Enabled | Playwright | Major Finnish rental company |
| oikotie.fi | Enabled | Playwright | Largest Finnish housing site |
| lumo.fi | Enabled | Playwright | Kojamo/Lumo (~39,000 apartments) |
| ta.fi | Enabled | Playwright | TA-Asunnot (5,000+ apartments) |
| rettamanagement.fi | Enabled | Playwright | Retta Management (~1,000 listings) |
| avara.fi | Enabled | JSON API | Avara (~7,000 apartments) |
| keva.fi | Enabled | HTML | Keva pension fund (~3,500 apartments) |
| ovv.com | Enabled | Playwright | OVV/Auroranlinna (~6,000 apartments) |
| vuokraovi.com | Disabled | - | Blocks headless browsers |

## Commute Calculation

Uses [OSRM](http://project-osrm.org/) free routing API:
- **Bike**: Cycling route with realistic times
- **Car**: Driving route (no traffic)
- **Transit**: Distance-based heuristic for Amsterdam; HSL Digitransit API for Helsinki

### City Configurations

| City | Office Target | Price Range | Min Surface | Min Rooms |
|------|--------------|-------------|-------------|-----------|
| Amsterdam | Stroombaan 4, Amstelveen | EUR 1000-2000 | - | - |
| Helsinki | Keilasatama 5, Espoo | EUR 800-1800 | 40 m² | 2 |

Helsinki uses the [HSL Digitransit API](https://digitransit.fi/en/developers/) for accurate public transit times including metro, tram, and bus.

## Neighborhood Scores

Hardcoded scores (1-10) for districts in each city.

### Amsterdam Districts (sample)

| Area | Safety | Green | Amenities | Restaurants | Family | Expat |
|------|--------|-------|-----------|-------------|--------|-------|
| Centrum | 7 | 4 | 10 | 10 | 5 | 9 |
| Zuid | 9 | 7 | 9 | 9 | 8 | 10 |
| West | 8 | 6 | 8 | 9 | 7 | 8 |
| Oost | 8 | 7 | 8 | 8 | 8 | 8 |
| Noord | 7 | 8 | 6 | 6 | 7 | 6 |
| Amstelveen | 9 | 9 | 7 | 6 | 9 | 9 |

### Helsinki Districts (sample)

| Area | Safety | Green | Amenities | Restaurants | Family | Expat |
|------|--------|-------|-----------|-------------|--------|-------|
| Kamppi | 7 | 4 | 10 | 10 | 5 | 9 |
| Kallio | 7 | 5 | 9 | 9 | 6 | 9 |
| Töölö | 9 | 7 | 8 | 8 | 7 | 8 |
| Punavuori | 8 | 4 | 9 | 10 | 5 | 9 |
| Lauttasaari | 9 | 7 | 7 | 6 | 8 | 7 |
| Tapiola (Espoo) | 9 | 8 | 8 | 7 | 9 | 8 |

See `utils/neighborhoods.py` for full list (26 Helsinki districts, 15+ Amsterdam areas).

## LLM Extraction (Optional)

The scraper can use a local Ollama LLM to extract structured data:

```bash
# Start Ollama with llama3
ollama run llama3

# Run scraper with LLM
rent-scraper scrape --sites pararius --model llama3
```

Without `--skip-llm`, uses regex fallback extraction which works well for most sites.

## Configuration

City configurations are in `src/amsterdam_rent_scraper/config/settings.py`. The `CITIES` dict contains per-city settings:

```python
CITIES = {
    "amsterdam": {
        "office_address": "Stroombaan 4, 1181 VX Amstelveen",
        "office_lat": 52.3027,
        "office_lon": 4.8557,
        "min_price": 1000,
        "max_price": 2000,
        "scrapers": ["pararius", "huurwoningen", ...],
    },
    "helsinki": {
        "office_address": "Keilasatama 5, 02150 Espoo, Finland",
        "office_lat": 60.1756,
        "office_lon": 24.8271,
        "min_price": 800,
        "max_price": 1800,
        "min_surface": 40,
        "min_rooms": 2,
        "scrapers": ["sato", "oikotie", "lumo", ...],
    },
}
```

## Requirements

- Python 3.10+
- Playwright Chromium (for JS-heavy sites)
- Internet connection (for OSRM API)
- Optional: Ollama with llama3 (for LLM extraction)

## License

MIT
