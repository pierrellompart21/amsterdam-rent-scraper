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
- Added `--min-surface` and `--min-rooms` CLI flags for post-extraction filtering
- Filters are applied after regex extraction, keeping listings without data for manual review

## CLI Options
```bash
# Install
pip install -e .
playwright install chromium

# Quick test (3 listings per site)
rent-scraper --test-run --sites pararius --skip-llm

# With surface and rooms filtering (recommended defaults: 60m2, 2 rooms)
rent-scraper --max-listings 10 --sites pararius --skip-llm --min-surface 60 --min-rooms 2

# Apartments only (filter out rooms/shared)
rent-scraper --max-listings 20 --sites kamernet --apartments-only --skip-llm

# Full run all working scrapers
rent-scraper --max-listings 50 --sites pararius,huurwoningen,123wonen,huurstunt,kamernet --skip-llm

# With LLM extraction (requires: ollama pull llama3.2 && ollama serve)
rent-scraper --max-listings 10 --sites pararius,huurwoningen
```

## Next Priority Tasks
1. **Progress bars**: Add tqdm/rich progress bars for per-site progress (pages/listings found)
2. **Default full pagination**: When no --max-listings, scrape ALL pages until no more results
3. **Commute calculation**: Use OSRM API for bike/transit times to Stroombaan 4, Amstelveen
4. **Neighborhood quality**: Add hardcoded Amsterdam neighborhood scores
5. **HTML report improvements**: Interactive filters, card layout, commute route on map click
6. **Search for missing rental sites**: vbo.nl, jaap.nl, mvgm.nl, vesteda.com, holland2stay.com
7. **SQLite database**: Store listings with deduplication by URL

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI with --min-surface, --min-rooms options
- `src/amsterdam_rent_scraper/pipeline.py` - Post-extraction filtering (price, apartments-only, surface, rooms)
- `src/amsterdam_rent_scraper/export/html_report.py` - Leaflet map with price-colored markers
- `src/amsterdam_rent_scraper/config/settings.py` - Site configs, work location coords

## Technical Notes
- Post-extraction filtering keeps listings without data (null surface/rooms) for manual review
- Filters run after regex/LLM extraction to catch sites that don't respect URL params
- Work location: Stroombaan 4, 1181 VX Amstelveen (52.3027, 4.8557)
