# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: project structure, CLI, pipeline, export modules
- **Working scrapers** (tested with `--skip-llm`):
  - `pararius` - works well
  - `huurwoningen` - uses JSON-LD structured data
  - `123wonen` - uses JSON-LD + HTML fallback
- **LLM extraction module** ready (requires Ollama running with llama3/mistral)
- **Export working**: Excel with styled columns, interactive HTML with Leaflet map

## Next Priority Tasks
1. **Test LLM extraction** with Ollama running locally:
   ```bash
   rent-scraper --test-run --sites pararius
   # (without --skip-llm, requires ollama with llama3 or mistral)
   ```

2. **Add Playwright support** for JS-heavy sites. Sites needing JS:
   - `directwonen` - listings load via AJAX
   - `huurstunt` - listings load via AJAX
   - `funda` - needs JS, aggressive anti-bot
   - `kamernet` - needs JS
   - `housinganywhere` - needs JS
   - `rentslam` - needs JS
   - `roofz` - needs JS

3. **Add fallback regex extraction** for when LLM output is incomplete

4. **Polish HTML report**:
   - Add commute overlay to Stroombaan 4, 1181 VX Amstelveen (lat: 52.3027, lon: 4.8557)
   - Color markers by price range

## How to Test
```bash
pip install -e .
# Test all working scrapers (no LLM):
rent-scraper --test-run --sites pararius,huurwoningen,123wonen --skip-llm
# View output/amsterdam_rentals.html in browser
```

## Key Files
- `src/amsterdam_rent_scraper/scrapers/base.py` - base scraper class
- `src/amsterdam_rent_scraper/scrapers/pararius.py` - reference implementation
- `src/amsterdam_rent_scraper/scrapers/huurwoningen.py` - JSON-LD based
- `src/amsterdam_rent_scraper/scrapers/wonen123.py` - JSON-LD + HTML fallback
- `src/amsterdam_rent_scraper/config/settings.py` - site configs + scraper class paths
- `src/amsterdam_rent_scraper/pipeline.py` - main orchestration

## Notes
- Each new scraper needs: `get_listing_urls()` and `parse_listing_page()` methods
- Site config in settings.py maps site name to scraper class path
- `needs_js=True` in RentalSite config marks JS-required sites (not yet handled)
- For Playwright support, need to add async variant to base.py
