# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: CLI, pipeline, export modules
- **Working scrapers** (all tested with regex fallback extraction):
  - `pararius` - HTML-based, reliable extraction
  - `huurwoningen` - JSON-LD structured data
  - `123wonen` - JSON-LD + HTML fallback
  - `huurstunt` - Playwright-based
  - `kamernet` - Playwright-based, extracts title/address from URL
  - `iamexpat` - **NEW** Playwright-based, Next.js site, uses domcontentloaded wait
- **Disabled/Not Implemented scrapers**:
  - `funda` - aggressive anti-bot
  - `housinganywhere` - blocks headless browsers
  - `rentslam` - not loading listings
  - `roofz` - site timing out
  - `directwonen` - requires login/subscription
  - `holland2stay` - robots.txt disallows /residences/ (unit listings page)
  - `vesteda` - complex API, dynamic content doesn't load in headless
  - `onlyexpats` - robots.txt blocks ClaudeBot/anthropic-ai

## Recent Changes (this iteration)
- **New IamExpat scraper** (`src/amsterdam_rent_scraper/scrapers/iamexpat.py`):
  - Playwright-based for Next.js site
  - Uses `domcontentloaded` instead of `networkidle` (avoids timeout on Next.js)
  - URL pattern: `/housing/rental-properties/amsterdam/{type}/{id}`
  - Extracts: price, surface, rooms, furnished status, address from street names
  - Registered in `config/settings.py`

## CLI Options
```bash
# Install
pip install -e .
playwright install chromium

# Quick test (3 listings per site, limited pages)
rent-scraper scrape --test-run --sites pararius --skip-llm

# Test IamExpat scraper
rent-scraper scrape --test-run --sites iamexpat --skip-llm

# With surface/rooms filters
rent-scraper scrape --max-listings 10 --sites pararius --skip-llm --min-surface 60 --min-rooms 2

# Full run - scrapes ALL available listings (paginates until no more results)
rent-scraper scrape --sites pararius,huurwoningen,iamexpat --skip-llm

# Re-export from database without scraping
rent-scraper export --format both
rent-scraper export --format html --min-price 1200 --max-price 1800 --source pararius

# Check database stats
rent-scraper db-info
```

## Next Priority Tasks
1. **README.md** - Setup instructions, usage examples, architecture overview
2. **More scrapers** (if time permits):
   - Research other sites with permissive robots.txt
   - Potential: expatrentals.eu, expathousingnetwork.nl

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI with scrape, export, db-info commands
- `src/amsterdam_rent_scraper/pipeline.py` - Post-extraction filtering, rich progress bars, DB storage
- `src/amsterdam_rent_scraper/storage/database.py` - SQLite database with deduplication
- `src/amsterdam_rent_scraper/utils/geo.py` - OSRM routing, geocoding, commute calculations
- `src/amsterdam_rent_scraper/utils/neighborhoods.py` - Neighborhood scores and detection
- `src/amsterdam_rent_scraper/models/listing.py` - RentalListing with commute and neighborhood fields
- `src/amsterdam_rent_scraper/export/html_report.py` - Interactive HTML with cards/table/map views, price slider
- `src/amsterdam_rent_scraper/export/excel.py` - Excel export with neighborhood columns
- `src/amsterdam_rent_scraper/scrapers/iamexpat.py` - **NEW** IamExpat Playwright scraper

## Technical Notes
- OSRM API: `http://router.project-osrm.org/route/v1/{cycling|driving}/lon1,lat1;lon2,lat2?overview=full&geometries=geojson`
- Transit times still use heuristic (OSRM doesn't have transit routing)
- Neighborhood detection priority: city name → aliases → direct name match → postal code ranges
- Neighborhood scores are 1-10, overall is weighted average
- Target: Stroombaan 4, 1181 VX Amstelveen (52.3027, 4.8557)
- Price range: EUR 1000-2000, Min surface: 60m2, Min rooms: 2
- Database: SQLite at `output/listings.db`, auto-created on first scrape
- **Next.js sites**: Use `domcontentloaded` wait instead of `networkidle` to avoid timeouts
