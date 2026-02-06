# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: CLI, pipeline, export modules
- **LLM extraction tested and working** with Ollama llama3.2
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

## CLI Options
```bash
# Install
pip install -e .
playwright install chromium

# Quick test (3 listings per site)
rent-scraper --test-run --sites pararius --skip-llm

# With pre-filters (NEW!)
rent-scraper --max-listings 10 --sites pararius --skip-llm --min-surface 60 --min-rooms 2

# With LLM extraction (requires: ollama pull llama3.2 && ollama serve)
rent-scraper --max-listings 10 --sites pararius,huurwoningen

# Full run all working scrapers (with regex extraction)
rent-scraper --max-listings 50 --sites pararius,huurwoningen,123wonen,huurstunt,kamernet --skip-llm

# Apartments only (filter out rooms/shared)
rent-scraper --max-listings 20 --sites kamernet --apartments-only --skip-llm
```

## Recent Changes (This Iteration)
- **Added CLI pre-filters**: `--min-surface` and `--min-rooms` options
- **Improved progress display**: Rich progress bars with panel showing all config options
- **Full pagination**: Scrapers now paginate up to 500 pages in full mode (until no more results)

## Next Priority Tasks
1. **Commute calculation**: For each listing, compute real commute time to Stroombaan 4, Amstelveen (52.3027, 4.8557). Use OSRM (free, no key) for bike/transit times. Show route on map click.
2. **Neighborhood quality**: Add quality-of-life scores per district (safety, green space, amenities, nightlife, family-friendly)
3. **HTML report improvements**:
   - Interactive filters (price slider, surface, rooms, commute time, neighborhood score)
   - Cards layout instead of table
   - Click marker -> show commute route + details popup
4. **Search for missing rental sites**: vbo.nl, jaap.nl, mvgm.nl, vesteda.com, holland2stay.com
5. **SQLite database**: Store all listings with deduplication by URL
6. **README.md**: Setup instructions, usage examples, architecture overview

## User Requirements
- Surface should be at least 60m² with at least 2 rooms
- These should be interactive filters in HTML report with sensible defaults
- CLI pre-filters: price range, min rooms, min surface (DONE!)
- Standard version iterates all pages when no max_listings (DONE!)
- Progress bars showing per-site progress (DONE!)

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI options
- `src/amsterdam_rent_scraper/pipeline.py` - Price/size filtering, progress bars
- `src/amsterdam_rent_scraper/export/html_report.py` - HTML report with filters
- `src/amsterdam_rent_scraper/scrapers/` - All scraper implementations

## Technical Notes
- Scrapers stop paginating early once `max_listings` reached (perf optimization)
- Post-extraction price/surface/rooms filtering catches listings where sites don't respect URL params
- LLM extraction via Ollama produces high-quality summaries and structured data
- Progress bars use rich library for polished terminal output
- Full mode now paginates up to 500 pages (effectively unlimited for most sites)
