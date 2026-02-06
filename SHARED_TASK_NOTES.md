# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: CLI, pipeline, export, database, commute calculation, neighborhoods
- **README.md complete** - Setup, usage, architecture, configuration documented
- **Transit routing NOW WORKING** - Uses Transitous (MOTIS API) for real public transit times
- **Working scrapers** (9 total, all tested with regex fallback extraction):
  - `pararius` - HTML-based, reliable extraction
  - `huurwoningen` - JSON-LD structured data
  - `123wonen` - JSON-LD + HTML fallback
  - `huurstunt` - Playwright-based
  - `kamernet` - Playwright-based, extracts title/address from URL
  - `iamexpat` - Playwright-based, Next.js site, uses domcontentloaded wait
  - `rotsvast` - HTML-based, Dutch rental agency
  - `expathousingnetwork` - Playwright-based, Webflow site, expat-focused
  - `huure` - HTML-based, Dutch rental aggregator, cursor-based pagination
- **Disabled scrapers**:
  - `funda` - aggressive anti-bot
  - `housinganywhere` - blocks headless browsers
  - `rentslam` - not loading listings
  - `roofz` - site timing out
  - `directwonen` - requires login/subscription
  - `holland2stay` - robots.txt disallows /residences/
  - `vesteda` - complex API, dynamic content doesn't load
  - `onlyexpats` - robots.txt blocks ClaudeBot/anthropic-ai
  - `expatrentals.eu` - robots.txt blocks AI training/scraping
- **Evaluated but not implemented**:
  - `nestpick` - Meta-search aggregator (would cause duplicates), no public API
  - `huisly` - Also an aggregator (1,200+ sources), would cause duplicates

## CLI Quick Reference
```bash
# Install
pip install -e . && playwright install chromium

# Test run
rent-scraper scrape --test-run --sites pararius --skip-llm

# Full scrape (all enabled sites)
rent-scraper scrape --sites pararius,huurwoningen,iamexpat,rotsvast,expathousingnetwork,huure --skip-llm

# Higher price range (expathousingnetwork has premium listings)
rent-scraper scrape --sites expathousingnetwork --skip-llm --max-price 5000

# Export from DB
rent-scraper export --format html --min-price 1200 --max-price 1800

# DB stats
rent-scraper db-info
```

## Completed Features
- CLI with scrape, export, db-info commands
- SQLite database with deduplication
- OSRM routing (bike/car times, route polylines)
- **Transitous API for real transit routing** (duration + transfers)
- Neighborhood detection and scoring
- Interactive HTML report (cards/table/map views, filters, route display)
- Excel export with all fields
- 9 working scrapers

## Next Priority Tasks
1. **Project is feature-complete** - All major features implemented
2. **Polish/testing** (optional) - Run a full scrape to verify everything works

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI commands
- `src/amsterdam_rent_scraper/pipeline.py` - Main orchestration
- `src/amsterdam_rent_scraper/storage/database.py` - SQLite with deduplication
- `src/amsterdam_rent_scraper/utils/geo.py` - OSRM + Transitous routing
- `src/amsterdam_rent_scraper/utils/neighborhoods.py` - Neighborhood scores
- `src/amsterdam_rent_scraper/export/html_report.py` - Interactive HTML
- `src/amsterdam_rent_scraper/scrapers/huure.py` - Huure.nl scraper

## Technical Notes
- **OSRM API**: `http://router.project-osrm.org/route/v1/{cycling|driving}/lon1,lat1;lon2,lat2?overview=full&geometries=geojson`
- **Transitous API**: `https://api.transitous.org/api/v1/plan?fromPlace=lat,lon&toPlace=lat,lon&directModes=WALK&transitModes=TRANSIT`
  - Free, no API key needed
  - Returns duration + number of transfers
  - Don't specify a time param (GTFS data may not cover future dates)
- Target: Stroombaan 4, Amstelveen (52.3027, 4.8557)
- Database: `output/listings.db`
- **Next.js sites**: Use `domcontentloaded` wait instead of `networkidle`
- **Webflow sites**: Similar to Next.js, use `domcontentloaded` with scroll for lazy loading
- **Huure.nl**: Uses cursor-based pagination (cursor1, cursor2 params)
- **ExpatHousingNetwork**: Listings often €2000+, may need higher --max-price filter
- **Rotsvast**: Listings often €2000+, may need higher --max-price filter
