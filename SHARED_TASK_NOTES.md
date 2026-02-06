# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: project structure, CLI, pipeline, export modules
- **Working scrapers** (tested with --skip-llm):
  - `pararius` - HTML-based, works well
  - `huurwoningen` - uses JSON-LD structured data
  - `123wonen` - uses JSON-LD + HTML fallback
  - `directwonen` - **NEW** Playwright-based, JS-heavy site
  - `huurstunt` - **NEW** Playwright-based, JS-heavy site
- **Playwright support added**: New `PlaywrightBaseScraper` class in `scrapers/playwright_base.py`
- **LLM extraction working**: Requires Ollama running with `llama3.2` model
- **Export working**: Excel with styled columns, interactive HTML with Leaflet map

## How to Test
```bash
pip install -e .

# Install Playwright browsers (first time only)
playwright install chromium

# Test all scrapers without LLM
rent-scraper --test-run --sites pararius,huurwoningen,123wonen,directwonen,huurstunt --skip-llm

# Test with LLM (requires: ollama pull llama3.2 && ollama serve)
rent-scraper --test-run --sites pararius,huurwoningen,123wonen

# View output/amsterdam_rentals.html in browser
```

## Next Priority Tasks
1. **Add more Playwright scrapers** for remaining JS-heavy sites:
   - `funda` - needs JS, aggressive anti-bot (may need extra stealth)
   - `kamernet` - needs JS
   - `housinganywhere` - needs JS
   - `rentslam` - needs JS (aggregator)
   - `roofz` - needs JS

2. **Add fallback regex extraction** for when LLM output is incomplete

3. **Polish HTML report**:
   - Add price/rooms/distance filters
   - Color markers by price range
   - Add commute overlay to Stroombaan 4 (lat: 52.3027, lon: 4.8557)

## Key Files
- `src/amsterdam_rent_scraper/scrapers/base.py` - base scraper class (HTTP-based)
- `src/amsterdam_rent_scraper/scrapers/playwright_base.py` - **NEW** Playwright base class for JS sites
- `src/amsterdam_rent_scraper/scrapers/pararius.py` - reference HTTP implementation
- `src/amsterdam_rent_scraper/scrapers/directwonen.py` - reference Playwright implementation
- `src/amsterdam_rent_scraper/llm/extractor.py` - LLM extraction
- `src/amsterdam_rent_scraper/config/settings.py` - site configs + OLLAMA_MODEL setting
- `src/amsterdam_rent_scraper/pipeline.py` - main orchestration

## Notes
- HTTP scrapers: inherit from `BaseScraper`, implement `get_listing_urls()` and `parse_listing_page()`
- Playwright scrapers: inherit from `PlaywrightBaseScraper`, same methods but `get_listing_urls(page)` gets a Playwright Page object
- Site config in settings.py: `needs_js=True` marks Playwright-required sites
- OLLAMA_MODEL defaults to "llama3.2" in settings.py - change if using different model
- DirectWonen URL pattern: `/huurwoningen-huren/amsterdam/STREET/TYPE-ID`
- Huurstunt URL pattern: `/TYPE/huren/in/amsterdam/STREET/ID`
