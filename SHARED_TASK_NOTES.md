# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: project structure, CLI, pipeline, export modules
- **Working scraper**: Pararius (tested with `rent-scraper --test-run --sites pararius --skip-llm`)
- **LLM extraction module** ready (requires Ollama running with llama3/mistral)
- **Export working**: Excel with styled columns, interactive HTML with Leaflet map

## Next Priority Tasks
1. **Implement remaining scrapers** (in order of difficulty):
   - `huurwoningen` - no JS needed, similar to pararius
   - `directwonen` - no JS needed
   - `huurstunt` - no JS needed
   - `123wonen` - no JS needed
   - `kamernet` - needs JS (Playwright/Selenium)
   - `funda` - needs JS, aggressive anti-bot
   - `housinganywhere` - needs JS
   - `rentslam` - needs JS, aggregator
   - `roofz` - needs JS

2. **Add Playwright/Selenium support** for JS-heavy sites (base.py needs async variant)

3. **Test LLM extraction** with Ollama running locally

## How to Test
```bash
pip install -e .
rent-scraper --test-run --sites pararius --skip-llm
# View output/amsterdam_rentals.html in browser
```

## Key Files
- `src/amsterdam_rent_scraper/scrapers/base.py` - base scraper class
- `src/amsterdam_rent_scraper/scrapers/pararius.py` - reference implementation
- `src/amsterdam_rent_scraper/config/settings.py` - site configs + scraper class paths
- `src/amsterdam_rent_scraper/pipeline.py` - main orchestration

## Notes
- Each new scraper needs: `get_listing_urls()` and `parse_listing_page()` methods
- Site config in settings.py maps site name to scraper class path
- For JS sites, set `needs_js=True` in RentalSite config (not yet handled in base)
