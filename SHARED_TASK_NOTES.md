# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: project structure, CLI, pipeline, export modules
- **Working scrapers** (tested with --skip-llm):
  - `pararius` - HTML-based, works well
  - `huurwoningen` - uses JSON-LD structured data
  - `123wonen` - uses JSON-LD + HTML fallback
  - `directwonen` - Playwright-based, JS-heavy site
  - `huurstunt` - Playwright-based, JS-heavy site
  - `kamernet` - Playwright-based, uses Dutch URLs (/huren/)
- **Disabled scrapers** (anti-bot or not working):
  - `funda` - aggressive anti-bot blocks headless browsers
  - `housinganywhere` - blocks headless browsers
  - `rentslam` - not loading individual listings
  - `roofz` - site timing out/not responding
- **Regex fallback extraction**: Added in `llm/regex_fallback.py` - extracts price, surface, rooms, postal code, etc. when LLM is unavailable
- **HTML report improvements**:
  - Colored markers by price (green < 1300, orange 1300-1700, red > 1700)
  - Commute distance circles (5/10/15 km) around office
  - Map legend for price and distance
  - Price-colored table cells
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
1. **Test LLM extraction** with Ollama (priority 4 from original list):
   - Run: `ollama pull llama3.2 && ollama serve`
   - Test: `rent-scraper --test-run --sites pararius`
   - Fix any JSON parsing issues in extractor

2. **Fix broken scrapers** - investigate if stealth options can bypass anti-bot:
   - funda: try playwright-stealth or different browser fingerprints
   - housinganywhere: same as above
   - roofz: check if site is actually up

3. **Run full (non-test) scrape** and validate output quality

## Key Files
- `src/amsterdam_rent_scraper/scrapers/base.py` - base HTTP scraper class
- `src/amsterdam_rent_scraper/scrapers/playwright_base.py` - Playwright base class for JS sites
- `src/amsterdam_rent_scraper/llm/extractor.py` - LLM extraction (uses regex fallback automatically)
- `src/amsterdam_rent_scraper/llm/regex_fallback.py` - Regex patterns for price, m2, rooms, etc.
- `src/amsterdam_rent_scraper/export/html_report.py` - HTML report with map
- `src/amsterdam_rent_scraper/config/settings.py` - site configs + OLLAMA_MODEL setting

## Notes
- HTTP scrapers: inherit from `BaseScraper`, implement `get_listing_urls()` and `parse_listing_page()`
- Playwright scrapers: inherit from `PlaywrightBaseScraper`, same methods but with Playwright Page object
- Site config in settings.py: `needs_js=True` marks Playwright-required sites, `enabled=False` disables broken scrapers
- OLLAMA_MODEL defaults to "llama3.2" in settings.py
- Regex fallback runs automatically after LLM extraction (or instead of it when --skip-llm or Ollama unavailable)
