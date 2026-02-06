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
- Added `--min-surface` and `--min-rooms` CLI filters (post-extraction filtering)
- Replaced tqdm with rich progress bars for consistent polished UI
- Implemented full pagination: when no --max-listings set, scrapes ALL pages until exhausted

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

# Limited full run
rent-scraper --max-listings 50 --sites pararius,huurwoningen,123wonen,huurstunt,kamernet --skip-llm
```

## Next Priority Tasks
1. **Commute calculation**: Add real commute times to target (Stroombaan 4, Amstelveen) via OpenRouteService/OSRM
2. **Neighborhood quality**: Add quality-of-life scores per Amsterdam district
3. **HTML report improvements**: Interactive filters, colored markers by price, commute route overlay
4. **More rental sites**: Search for vbo.nl, jaap.nl, vesteda.com, holland2stay.com
5. **SQLite database**: Store listings with deduplication by URL
6. **README.md**: Setup instructions, usage examples, architecture overview

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI with --apartments-only, --min-surface, --min-rooms
- `src/amsterdam_rent_scraper/pipeline.py` - Post-extraction filtering, rich progress bars
- `src/amsterdam_rent_scraper/scrapers/base.py` - Base scraper with rich progress, max_listings=None means unlimited
- `src/amsterdam_rent_scraper/scrapers/playwright_base.py` - Playwright base with same behavior

## Technical Notes
- Post-extraction filtering: price, apartments-only, min-surface, min-rooms
- Field names: `surface_m2` (not surface_sqm), `rooms`, `price_eur`
- max_listings=None (default in full mode) = paginate until no more results
- Target: Stroombaan 4, 1181 VX Amstelveen (52.3027, 4.8557)
- Price range: EUR 1000-2000, Min surface: 60m², Min rooms: 2
