# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: CLI, pipeline, export modules
- **Working scrapers** (all tested with regex fallback extraction):
  - `pararius` - HTML-based, reliable price/size/rooms extraction
  - `huurwoningen` - JSON-LD structured data
  - `123wonen` - JSON-LD + HTML fallback
  - `directwonen` - Playwright-based (some timeouts, ~7/19 with area/rooms)
  - `huurstunt` - Playwright-based
  - `kamernet` - Playwright-based, Dutch URLs (includes rooms, not just apartments)
- **Disabled scrapers** (anti-bot or not working):
  - `funda` - aggressive anti-bot blocks headless browsers
  - `housinganywhere` - blocks headless browsers
  - `rentslam` - not loading individual listings
  - `roofz` - site timing out/not responding

## CLI Options
```bash
# Install
pip install -e .
playwright install chromium

# Quick test (3 listings per site)
rent-scraper --test-run --sites pararius --skip-llm

# Moderate run with custom limit
rent-scraper --max-listings 20 --sites pararius,huurwoningen,123wonen --skip-llm

# Full run all working scrapers
rent-scraper --max-listings 50 --sites pararius,huurwoningen,123wonen,directwonen,huurstunt,kamernet --skip-llm

# With LLM extraction (requires: ollama pull llama3.2 && ollama serve)
rent-scraper --max-listings 10 --sites pararius,huurwoningen
```

## Data Quality Observations (from 101 listings test)
1. **Pararius**: Best quality - all 20 listings have price/area/rooms
2. **Huurwoningen**: Returns listings outside price range (aggregates from multiple sources)
3. **123wonen**: Price filter not respected - shows listings above 2000 EUR
4. **Directwonen**: Only ~7/19 have area/rooms extracted (needs parser improvement)
5. **Kamernet**: Includes rooms + apartments, some prices outside range, missing titles

## Next Priority Tasks
1. **Add data quality filters in pipeline**:
   - Filter listings by price range after extraction (not just at search URL)
   - Option to filter out rooms/shared housing

2. **Improve directwonen parser**: Area/rooms extraction failing for most listings

3. **Fix kamernet title extraction**: Most titles coming back as None

4. **Test LLM extraction**: Run with --sites pararius (no --skip-llm) to validate Ollama integration

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI entry point with --max-listings option
- `src/amsterdam_rent_scraper/pipeline.py` - Orchestrates scraping, extraction, export
- `src/amsterdam_rent_scraper/scrapers/base.py` - Base HTTP scraper class
- `src/amsterdam_rent_scraper/scrapers/playwright_base.py` - Playwright base class
- `src/amsterdam_rent_scraper/llm/regex_fallback.py` - Regex patterns for extraction
- `src/amsterdam_rent_scraper/export/html_report.py` - HTML report with Leaflet map
- `src/amsterdam_rent_scraper/config/settings.py` - Site configs, OLLAMA_MODEL setting

## Technical Notes
- `--max-listings N` overrides both test-mode (3) and full-mode (10000) defaults
- Geocoding uses Nominatim with 1 req/sec rate limit
- HTML report has colored markers by price range and commute distance circles
- Regex fallback runs automatically when LLM skipped or unavailable
