# Multi-City Rent Scraper - Task Notes

## Current State: HELSINKI MODE WORKING - 5 SCRAPERS

Helsinki now has 5 working scrapers. The pipeline is fully functional.

### What Works
- `rent-scraper scrape --city helsinki` - All 5 scrapers working
- City-specific database: `output/helsinki_listings.db`
- City-specific exports: `output/helsinki_rentals.html`, `output/helsinki_rentals.xlsx`
- HSL transit routing calculating proper commute times to Keilasatama 5, Espoo
- Helsinki neighborhood quality scores (26 districts)
- Price/surface/room filtering all working correctly

### Working Helsinki Scrapers
1. **SATO** (`sato`) - Major Finnish rental company. Next.js site, works with Playwright.
2. **Oikotie** (`oikotie`) - Largest Finnish housing site. AngularJS site, works with Playwright.
3. **LUMO** (`lumo`) - Kojamo/Lumo apartments (~39,000 units across Finland). React/Redux site.
4. **TA** (`ta`) - TA-Asunnot with 5,000+ apartments. WordPress site with server-rendered HTML.
5. **Retta** (`retta`) - **NEW** Retta Management (~1,000 Helsinki area listings). Next.js site with all data in `__NEXT_DATA__`. Very fast scraping since no individual page fetches needed.

### Blocked/Disabled Scrapers
1. **Vuokraovi** (`vuokraovi`) - Blocks headless browsers completely. Disabled.

## Next Steps: MORE HELSINKI SCRAPERS

Potential sites to implement (in priority order):
1. **A-Kruunu** (a-kruunu.fi) - Affordable rentals in Helsinki metro area. Uses external search at `a-kruunu-markkinointihaku.etampuuri.fi` which is a Knockout.js app - more complex to scrape than standard sites.
2. **forenom.com** - Furnished/temporary rentals. Previously blocked with 403.
3. **housinganywhere.com** - Already have scraper for Amsterdam but it's disabled (blocks headless browsers).

### Research Notes

**Etuovi.com:**
- Does NOT have rental listings - only sales (myytävät asunnot)
- Rental listings redirect to vuokraovi.com (same parent company)
- Skip this site for rentals

**A-Kruunu (a-kruunu.fi):**
- Main site is Drupal-based, redirects apartment search to external platform
- Apartment search at `a-kruunu-markkinointihaku.etampuuri.fi` uses Knockout.js
- Data loaded dynamically via AJAX, no easy JSON endpoint visible
- Would require Playwright + careful observation of network requests
- Lower priority due to complexity

**Retta Management (vuokraus.rettamanagement.fi):**
- Next.js site with all listings embedded in `__NEXT_DATA__` JSON
- ~1,614 total listings, ~1,000 in Helsinki metro area
- Very efficient - all data from single page load, no individual page fetches needed
- Successfully implemented!

## CLI Quick Reference
```bash
# Helsinki with all working scrapers
rent-scraper scrape --city helsinki --skip-llm
rent-scraper scrape --city helsinki --max-listings 20 --skip-llm

# Just retta (fastest scraper)
rent-scraper scrape --city helsinki --sites retta --skip-llm

# Check database
rent-scraper db-info --city helsinki

# Export only
rent-scraper export --city helsinki --format html

# Amsterdam (still works)
rent-scraper scrape --city amsterdam --test-run
```

## Key Files
- `src/amsterdam_rent_scraper/config/settings.py` - City configs, RentalSite entries
- `src/amsterdam_rent_scraper/scrapers/sato.py` - Working SATO scraper
- `src/amsterdam_rent_scraper/scrapers/oikotie.py` - Working Oikotie scraper
- `src/amsterdam_rent_scraper/scrapers/lumo.py` - Working LUMO scraper
- `src/amsterdam_rent_scraper/scrapers/ta.py` - Working TA-Asunnot scraper
- `src/amsterdam_rent_scraper/scrapers/retta.py` - Working Retta scraper (uses cached __NEXT_DATA__)
- `src/amsterdam_rent_scraper/scrapers/vuokraovi.py` - Blocked, disabled

## Technical Notes

### Finnish Site Considerations
- **Language**: Sites in Finnish. Key terms: vuokra (rent), asunto (apartment), huone (room), neliö (m²)
- **Postal codes**: 5 digits (00XXX = Helsinki, 01XXX = Vantaa, 02XXX = Espoo)
- **Price format**: "X €/kk" (euros per month), may have spaces in thousands, comma as decimal
- **Room format**: "3h+k" = 3 rooms + kitchen, "2h+kk" = 2 rooms + kitchenette
- **Sauna**: Very common in Finnish apartments, often abbreviated as "+s"

### Helsinki Office Target
- Address: Keilasatama 5, 02150 Espoo, Finland
- Coordinates: (60.1756, 24.8271)
- Transit API: HSL Digitransit (working)

## Project Status
- Amsterdam: COMPLETE (9 working scrapers)
- Helsinki: IN PROGRESS (5 working scrapers - SATO, Oikotie, LUMO, TA, Retta)

### Recent Changes
- Added Retta Management scraper with efficient __NEXT_DATA__ extraction (~1000 Helsinki listings)
