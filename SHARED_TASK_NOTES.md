# Multi-City Rent Scraper - Task Notes

## Current State: HELSINKI MODE WORKING - 3 SCRAPERS

Helsinki now has 3 working scrapers. The pipeline is fully functional.

### What Works
- `rent-scraper scrape --city helsinki` - All 3 scrapers working
- City-specific database: `output/helsinki_listings.db`
- City-specific exports: `output/helsinki_rentals.html`, `output/helsinki_rentals.xlsx`
- HSL transit routing calculating proper commute times to Keilasatama 5, Espoo
- Helsinki neighborhood quality scores (26 districts)
- Price/surface/room filtering all working correctly

### Working Helsinki Scrapers
1. **SATO** (`sato`) - Major Finnish rental company. Next.js site, works with Playwright.
2. **Oikotie** (`oikotie`) - Largest Finnish housing site. AngularJS site, works with Playwright.
3. **LUMO** (`lumo`) - **NEW** Kojamo/Lumo apartments (~39,000 units across Finland). React/Redux site. Needs cookie consent handling (CybotCookiebot), pagination via "Show more" button.

### Blocked/Disabled Scrapers
1. **Vuokraovi** (`vuokraovi`) - Blocks headless browsers completely. Returns "Enable JavaScript" even with Playwright. Disabled.

## Next Steps: MORE HELSINKI SCRAPERS

Potential sites (in priority order):
1. **forenom.fi** - Furnished/temporary rentals. Worth investigating.
2. **housinganywhere.com** - Already have scraper for Amsterdam. Could add Helsinki search params.
3. **kojamo.fi** - Parent company of LUMO, may have additional listings or API.

### Research Notes

**Etuovi.com:**
- Does NOT have rental listings - only sales (myytävät asunnot)
- Rental listings redirect to vuokraovi.com (same parent company)
- Skip this site for rentals

**LUMO Implementation Notes:**
- Cookie consent: Uses CybotCookiebot. Must handle `#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll` selector.
- Pagination: Uses "Näytä lisää asuntoja" (Show more apartments) button. Each click loads ~14 more listings.
- Site shows ALL of Finland by default - filter by city in URL path: `/vuokra-asunnot/Helsinki/...`
- Helsinki metro cities: Helsinki, Espoo, Vantaa, Kauniainen

## CLI Quick Reference
```bash
# Helsinki with all working scrapers
rent-scraper scrape --city helsinki --skip-llm
rent-scraper scrape --city helsinki --max-listings 20 --skip-llm

# Just lumo
rent-scraper scrape --city helsinki --sites lumo --skip-llm

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
- `src/amsterdam_rent_scraper/scrapers/vuokraovi.py` - Blocked, disabled

## Technical Notes

### Finnish Site Considerations
- **Language**: Sites in Finnish. Key terms: vuokra (rent), asunto (apartment), huone (room), neliö (m²)
- **Postal codes**: 5 digits (00XXX = Helsinki, 01XXX = Vantaa, 02XXX = Espoo)
- **Price format**: "X €/kk" (euros per month), may have spaces in thousands
- **Room format**: "3h+k" = 3 rooms + kitchen, "2h+kk" = 2 rooms + kitchenette
- **Sauna**: Very common in Finnish apartments, often abbreviated as "+s"

### Helsinki Office Target
- Address: Keilasatama 5, 02150 Espoo, Finland
- Coordinates: (60.1756, 24.8271)
- Transit API: HSL Digitransit (working)

## Project Status
- Amsterdam: COMPLETE (9 working scrapers)
- Helsinki: IN PROGRESS (3 working scrapers - SATO, Oikotie, LUMO)

### Recent Changes
- Added LUMO scraper with CybotCookiebot consent handling and pagination
- Confirmed etuovi.com only does sales (not rentals) - skip for this project
