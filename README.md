# Amsterdam Rent Scraper

A CLI tool to scrape rental listings from multiple Dutch housing websites, calculate commute times, analyze neighborhoods, and export to interactive HTML reports with maps.

## Features

- **Multi-site scraping** - Pararius, Huurwoningen, 123Wonen, Huurstunt, Kamernet, IamExpat
- **Commute calculation** - Real bike/driving times via OSRM routing API
- **Neighborhood scoring** - Safety, amenities, green space, restaurants, expat-friendliness (1-10)
- **SQLite database** - Persistent storage with deduplication
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

## CLI Commands

### `rent-scraper scrape`

Scrape rental websites and save to database.

| Option | Description | Default |
|--------|-------------|---------|
| `--test-run, -t` | Scrape only 3 listings per site | False |
| `--sites, -s` | Filter sites (comma-separated) | All enabled |
| `--max-listings, -n` | Max listings per site | Unlimited |
| `--min-price` | Minimum rent in EUR | 1000 |
| `--max-price` | Maximum rent in EUR | 2000 |
| `--min-surface` | Minimum surface area in m² | None |
| `--min-rooms` | Minimum number of rooms | None |
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

Listings are stored in `output/listings.db` (SQLite). The database:
- Deduplicates by URL
- Stores all listing fields including commute times and neighborhood scores
- Supports filtered queries for export

### HTML Report

Interactive report at `output/amsterdam_rentals.html`:
- **Cards view** - Visual cards with key info and neighborhood badges
- **Table view** - Sortable table with all fields
- **Map view** - Leaflet map with colored markers (green=cheap, yellow=mid, red=expensive)
- **Filters** - Price slider, surface/rooms/commute filters
- **Route display** - Click marker to show bike route to work

### Excel

Full data export at `output/amsterdam_rentals.xlsx` with all fields.

## Scraped Sites

| Site | Status | Method | Notes |
|------|--------|--------|-------|
| pararius.com | Enabled | HTML | Reliable, good structure |
| huurwoningen.nl | Enabled | HTML/JSON-LD | Structured data |
| 123wonen.nl | Enabled | HTML/JSON-LD | Good fallback extraction |
| huurstunt.nl | Enabled | Playwright | Dynamic content |
| kamernet.nl | Enabled | Playwright | Rooms and apartments |
| iamexpat.nl | Enabled | Playwright | Expat-focused, Next.js |
| funda.nl | Disabled | - | Aggressive anti-bot |
| housinganywhere.com | Disabled | - | Blocks headless browsers |
| directwonen.nl | Disabled | - | Requires subscription |

## Commute Calculation

Uses [OSRM](http://project-osrm.org/) free routing API:
- **Bike**: Cycling route with realistic times
- **Car**: Driving route (no traffic)
- **Transit**: Distance-based heuristic (OSRM doesn't support transit)

Default work location: Stroombaan 4, Amstelveen (configurable in `config/settings.py`)

## Neighborhood Scores

Hardcoded scores (1-10) for Amsterdam districts:

| Area | Safety | Green | Amenities | Restaurants | Family | Expat |
|------|--------|-------|-----------|-------------|--------|-------|
| Centrum | 7 | 4 | 10 | 10 | 5 | 9 |
| Zuid | 9 | 7 | 9 | 9 | 8 | 10 |
| West | 8 | 6 | 8 | 9 | 7 | 8 |
| Oost | 8 | 7 | 8 | 8 | 8 | 8 |
| Noord | 7 | 8 | 6 | 6 | 7 | 6 |
| Amstelveen | 9 | 9 | 7 | 6 | 9 | 9 |

See `utils/neighborhoods.py` for full list.

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

Edit `src/amsterdam_rent_scraper/config/settings.py`:

```python
# Work location for commute calculation
WORK_ADDRESS = "Stroombaan 4, 1181 VX Amstelveen"
WORK_LAT = 52.3027
WORK_LNG = 4.8557

# Default price range
MIN_PRICE = 1000
MAX_PRICE = 2000

# Scraping delays (be nice to servers)
REQUEST_DELAY_MIN = 2.0
REQUEST_DELAY_MAX = 5.0
```

## Requirements

- Python 3.10+
- Playwright Chromium (for JS-heavy sites)
- Internet connection (for OSRM API)
- Optional: Ollama with llama3 (for LLM extraction)

## License

MIT
