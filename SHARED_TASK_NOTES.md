# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: project structure, CLI, pipeline, export modules
- **Working scrapers** (tested with --skip-llm):
  - `pararius` - HTML-based, works well
  - `huurwoningen` - uses JSON-LD structured data
  - `123wonen` - uses JSON-LD + HTML fallback
  - `directwonen` - Playwright-based, JS-heavy site (can timeout sometimes)
  - `huurstunt` - Playwright-based, JS-heavy site
  - `kamernet` - **NEW** Playwright-based, uses Dutch URLs (/huren/)
- **Disabled scrapers** (anti-bot or not working):
  - `funda` - aggressive anti-bot blocks headless browsers
  - `housinganywhere` - blocks headless browsers
  - `rentslam` - not loading individual listings
  - `roofz` - site timing out/not responding
- **Playwright support**: `PlaywrightBaseScraper` class in `scrapers/playwright_base.py`
- **LLM extraction**: Requires Ollama with `llama3.2` model
- **Export**: Excel with styled columns, interactive HTML with Leaflet map

## How to Test
```bash
pip install -e .

# Install Playwright browsers (first time only)
playwright install chromium

# Test all working scrapers without LLM
rent-scraper --test-run --sites pararius,huurwoningen,123wonen,directwonen,huurstunt,kamernet --skip-llm

# Test with LLM (requires: ollama pull llama3.2 && ollama serve)
rent-scraper --test-run --sites pararius,huurwoningen,123wonen

# View output/amsterdam_rentals.html in browser
```

## Next Priority Tasks
1. **Add fallback regex extraction** for when LLM output is incomplete (priority 6)

2. **Polish HTML report** (priority 7):
   - Add price/rooms/distance filters
   - Color markers by price range (green < 1300, yellow 1300-1700, red > 1700)
   - Add commute overlay to Stroombaan 4 (lat: 52.3027, lon: 4.8557)

3. **Run full end-to-end test** with all working scrapers (priority 8)

4. **Fix broken scrapers** - investigate if stealth options can bypass anti-bot:
   - funda: try playwright-stealth or different browser fingerprints
   - housinganywhere: same as above
   - roofz: check if site is actually up

## Key Files
- `src/amsterdam_rent_scraper/scrapers/base.py` - base HTTP scraper class
- `src/amsterdam_rent_scraper/scrapers/playwright_base.py` - Playwright base class for JS sites
- `src/amsterdam_rent_scraper/scrapers/pararius.py` - reference HTTP implementation
- `src/amsterdam_rent_scraper/scrapers/directwonen.py` - reference Playwright implementation
- `src/amsterdam_rent_scraper/scrapers/kamernet.py` - Kamernet (Dutch URLs)
- `src/amsterdam_rent_scraper/llm/extractor.py` - LLM extraction
- `src/amsterdam_rent_scraper/config/settings.py` - site configs + OLLAMA_MODEL setting
- `src/amsterdam_rent_scraper/pipeline.py` - main orchestration

## Notes
- HTTP scrapers: inherit from `BaseScraper`, implement `get_listing_urls()` and `parse_listing_page()`
- Playwright scrapers: inherit from `PlaywrightBaseScraper`, same methods but `get_listing_urls(page)` gets a Playwright Page object
- Site config in settings.py: `needs_js=True` marks Playwright-required sites, `enabled=False` disables broken scrapers
- OLLAMA_MODEL defaults to "llama3.2" in settings.py
- Kamernet uses Dutch URLs: `/huren/kamer-amsterdam/STREET/kamer-ID`
