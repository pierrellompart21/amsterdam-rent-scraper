# Multi-City Rent Scraper - Task Notes

## Current State: HELSINKI MODE COMPLETE - 8 SCRAPERS

Helsinki mode is fully functional with 8 working scrapers. README updated with multi-city documentation.

### What Works
- `rent-scraper scrape --city helsinki` - All 8 scrapers working
- `rent-scraper scrape --city amsterdam` - Original Amsterdam scrapers still work
- City-specific databases: `output/helsinki_listings.db`, `output/amsterdam_listings.db`
- City-specific exports: HTML and Excel per city
- HSL transit routing for Helsinki commute times
- Helsinki neighborhood quality scores (26 districts)
- README updated with Helsinki documentation

### Working Helsinki Scrapers (8 total)
1. **SATO** (`sato`) - Major Finnish rental company. Playwright.
2. **Oikotie** (`oikotie`) - Largest Finnish housing site. Playwright.
3. **LUMO** (`lumo`) - Kojamo/Lumo apartments (~39,000 units). Playwright.
4. **TA** (`ta`) - TA-Asunnot (5,000+ apartments). Playwright.
5. **Retta** (`retta`) - Retta Management (~1,000 listings). Playwright + __NEXT_DATA__.
6. **Avara** (`avara`) - Pure JSON API. Fastest scraper.
7. **Keva** (`keva`) - HTML scraping. No Playwright needed.
8. **OVV** (`ovv`) - Playwright + API interception.

### Blocked/Disabled
- **Vuokraovi** - Blocks headless browsers

## Potential Next Steps

If more scrapers are needed:
- **M2-Kodit** (m2kodit.fi) - 11,500 ARA-subsidized apartments. Complex Vue.js/WordPress AJAX.
- **A-Kruunu** (a-kruunu.fi) - Uses external etampuuri.fi search system.
- **Forenom** (forenom.com) - Returns 403 blocked.

All major sites are covered. The remaining sites are either complex to scrape or blocked.

## CLI Quick Reference
```bash
# Helsinki
rent-scraper scrape --city helsinki --skip-llm
rent-scraper db-info --city helsinki
rent-scraper export --city helsinki --format html

# Amsterdam
rent-scraper scrape --city amsterdam --test-run --skip-llm
rent-scraper db-info --city amsterdam
```

## Key Files
- `src/amsterdam_rent_scraper/config/settings.py` - City configs, CITIES dict
- `src/amsterdam_rent_scraper/scrapers/` - All scraper implementations
- `src/amsterdam_rent_scraper/utils/neighborhoods.py` - City-specific neighborhood scores
- `src/amsterdam_rent_scraper/utils/geo.py` - HSL Digitransit API for Helsinki transit

## Project Status
- Amsterdam: COMPLETE (9 working scrapers)
- Helsinki: COMPLETE (8 working scrapers)
- README: Updated with multi-city documentation
- Database: 63 Helsinki listings, working correctly

The multi-city rental scraper is feature-complete for both Amsterdam and Helsinki.
