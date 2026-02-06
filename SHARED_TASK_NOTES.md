# Amsterdam Rent Scraper - Task Notes

## Current State
- Core infrastructure complete: project structure, CLI, pipeline, export modules
- **Working scrapers** (tested with LLM extraction):
  - `pararius` - works well
  - `huurwoningen` - uses JSON-LD structured data
  - `123wonen` - uses JSON-LD + HTML fallback
- **LLM extraction working**: Requires Ollama running with `llama3.2` model
  - Extracts summaries, pros/cons, neighborhood info
  - Takes ~5-7 seconds per listing
- **Export working**: Excel with styled columns, interactive HTML with Leaflet map

## How to Test
```bash
pip install -e .

# Test with LLM (requires: ollama pull llama3.2 && ollama serve)
rent-scraper --test-run --sites pararius,huurwoningen,123wonen

# Test without LLM
rent-scraper --test-run --sites pararius,huurwoningen,123wonen --skip-llm

# View output/amsterdam_rentals.html in browser
```

## Next Priority Tasks
1. **Add Playwright support** for JS-heavy sites:
   - `directwonen` - listings load via AJAX
   - `huurstunt` - listings load via AJAX
   - `funda` - needs JS, aggressive anti-bot
   - `kamernet` - needs JS
   - `housinganywhere` - needs JS
   - `rentslam` - needs JS
   - `roofz` - needs JS

2. **Add fallback regex extraction** for when LLM output is incomplete

3. **Polish HTML report**:
   - Add commute overlay to Stroombaan 4 (lat: 52.3027, lon: 4.8557)
   - Color markers by price range

## Key Files
- `src/amsterdam_rent_scraper/scrapers/base.py` - base scraper class
- `src/amsterdam_rent_scraper/scrapers/pararius.py` - reference implementation
- `src/amsterdam_rent_scraper/llm/extractor.py` - LLM extraction
- `src/amsterdam_rent_scraper/config/settings.py` - site configs + OLLAMA_MODEL setting
- `src/amsterdam_rent_scraper/pipeline.py` - main orchestration

## Notes
- Each new scraper needs: `get_listing_urls()` and `parse_listing_page()` methods
- Site config in settings.py maps site name to scraper class path
- `needs_js=True` in RentalSite config marks JS-required sites (not yet handled)
- For Playwright support, need to add async variant to base.py
- OLLAMA_MODEL defaults to "llama3.2" in settings.py - change if using different model
