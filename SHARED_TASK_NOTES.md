# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: CLI, pipeline, export modules
- **Working scrapers** (all tested with regex fallback extraction):
  - `pararius` - HTML-based, reliable extraction
  - `huurwoningen` - JSON-LD structured data
  - `123wonen` - JSON-LD + HTML fallback
  - `huurstunt` - Playwright-based
  - `kamernet` - Playwright-based, extracts title/address from URL
- **Disabled scrapers**:
  - `funda` - aggressive anti-bot
  - `housinganywhere` - blocks headless browsers
  - `rentslam` - not loading listings
  - `roofz` - site timing out
  - `directwonen` - requires login/subscription to see prices and details

## Recent Changes (this iteration)
- **Neighborhood Quality Scores**: Hardcoded ratings for Amsterdam districts
  - New module: `utils/neighborhoods.py` with 30+ neighborhoods/municipalities
  - Scores 1-10 for: safety, green_space, amenities, restaurants, family_friendly, expat_friendly
  - Weighted overall score calculated automatically
  - Detection via city name, address text, postal code ranges
  - Integrated into `enrich_listing_with_geo()` - automatically added during pipeline
  - HTML report: sortable Area column with hover tooltip showing all scores
  - Excel export: 8 new columns (Neighborhood, Area Score, Safety, Green Space, etc.)
  - New filter: Min Neighborhood Score in HTML report

## CLI Options
```bash
# Install
pip install -e .
playwright install chromium

# Quick test (3 listings per site, limited pages)
rent-scraper --test-run --sites pararius --skip-llm

# With surface/rooms filters
rent-scraper --max-listings 10 --sites pararius --skip-llm --min-surface 60 --min-rooms 2

# Full run - scrapes ALL available listings (paginates until no more results)
rent-scraper --sites pararius,huurwoningen --skip-llm
```

## Next Priority Tasks
1. **SQLite database** - Store listings with deduplication by URL, add `export --format excel/html` command
2. **HTML report improvements** - Cards layout, price range slider, colored markers, modern CSS
3. **More rental sites** - Search for vesteda.com, holland2stay.com, iamexpat.nl/housing
4. **README.md** - Setup instructions, usage examples, architecture

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI with --apartments-only, --min-surface, --min-rooms
- `src/amsterdam_rent_scraper/pipeline.py` - Post-extraction filtering, rich progress bars
- `src/amsterdam_rent_scraper/utils/geo.py` - OSRM routing, geocoding, commute calculations
- `src/amsterdam_rent_scraper/utils/neighborhoods.py` - Neighborhood scores and detection
- `src/amsterdam_rent_scraper/models/listing.py` - RentalListing with commute and neighborhood fields
- `src/amsterdam_rent_scraper/export/html_report.py` - Interactive HTML with route display and neighborhood info
- `src/amsterdam_rent_scraper/export/excel.py` - Excel export with neighborhood columns

## Technical Notes
- OSRM API: `http://router.project-osrm.org/route/v1/{cycling|driving}/lon1,lat1;lon2,lat2?overview=full&geometries=geojson`
- Transit times still use heuristic (OSRM doesn't have transit routing)
- Neighborhood detection priority: city name → aliases → direct name match → postal code ranges
- Neighborhood scores are 1-10, overall is weighted average
- Target: Stroombaan 4, 1181 VX Amstelveen (52.3027, 4.8557)
- Price range: EUR 1000-2000, Min surface: 60m2, Min rooms: 2
