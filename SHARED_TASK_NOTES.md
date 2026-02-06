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
- Added post-extraction price filtering (filters listings outside EUR range after extraction)
- Added `--apartments-only` CLI flag to filter out rooms/shared housing
- Fixed Kamernet title/address extraction (derives from URL when not in HTML)
- Disabled DirectWonen (requires paywall/login to see actual rental prices)

## CLI Options
```bash
# Install
pip install -e .
playwright install chromium

# Quick test (3 listings per site)
rent-scraper --test-run --sites pararius --skip-llm

# Apartments only (filter out rooms/shared)
rent-scraper --max-listings 20 --sites kamernet --apartments-only --skip-llm

# Full run all working scrapers
rent-scraper --max-listings 50 --sites pararius,huurwoningen,123wonen,huurstunt,kamernet --skip-llm

# With LLM extraction (requires: ollama pull llama3.2 && ollama serve)
rent-scraper --max-listings 10 --sites pararius,huurwoningen
```

## Next Priority Tasks
1. **Test LLM extraction**: Run with `--sites pararius` (no --skip-llm) to validate Ollama integration
2. **Improve data quality**: Some sites don't respect URL price filters, now post-filtered in pipeline
3. **HTML report filters**: Add interactive price/rooms/distance filters to the HTML report
4. **Test with more listings**: Run `rent-scraper --max-listings 50 --sites pararius,huurwoningen,123wonen,huurstunt,kamernet --skip-llm` and verify data quality

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI with --apartments-only option
- `src/amsterdam_rent_scraper/pipeline.py` - Price filtering + apartments-only filtering
- `src/amsterdam_rent_scraper/scrapers/kamernet.py` - URL-based title/address extraction
- `src/amsterdam_rent_scraper/config/settings.py` - Site configs (directwonen disabled)

## Technical Notes
- Post-extraction price filtering catches listings where sites don't respect URL params
- `--apartments-only` filters by property_type, URL patterns, and title keywords
- Kamernet extracts title/address from URL pattern: `/huren/TYPE-amsterdam/STREET/TYPE-ID`
- DirectWonen disabled because all prices on page are subscription fees (€10.95, etc.)
