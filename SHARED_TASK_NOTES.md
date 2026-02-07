# Multi-City Rent Scraper - Task Notes

## Current State: HELSINKI MODE WORKING - 2 SCRAPERS

Helsinki now has 2 working scrapers. The pipeline is functional for Helsinki with proper filtering.

### What Works
- `rent-scraper scrape --city helsinki` - Both scrapers working
- City-specific database: `output/helsinki_listings.db`
- City-specific exports: `output/helsinki_rentals.html`, `output/helsinki_rentals.xlsx`
- HSL transit routing calculating proper commute times to Keilasatama 5, Espoo
- Helsinki neighborhood quality scores (26 districts)
- Price/surface/room filtering all working correctly

### Working Helsinki Scrapers
1. **SATO** (`sato`) - Major Finnish rental company. Works well with Playwright. ~27 listings available.
2. **Oikotie** (`oikotie`) - **NEW** Largest Finnish housing site. AngularJS site, works with Playwright. ~27+ listings per page.

### Blocked/Disabled Scrapers
1. **Vuokraovi** (`vuokraovi`) - Blocks headless browsers completely. Returns "Enable JavaScript" even with Playwright. Disabled.

## Next Steps: MORE HELSINKI SCRAPERS

Priority order for implementation:
1. **etuovi.com** - Finnish housing marketplace (same company as vuokraovi, may have same blocks)
2. **lumo.fi** - Kojamo/Lumo rentals. React SPA, navigation may be challenging.

### Research Notes

**Etuovi.com:**
- Same parent company as vuokraovi, likely same anti-bot measures
- React/Material-UI frontend
- Strong headless browser detection expected

**LUMO:**
- React Redux SPA
- Apartment cards don't have direct links - uses React Router
- May need to interact with cards via Playwright clicks

## CLI Quick Reference
```bash
# Helsinki with all working scrapers
rent-scraper scrape --city helsinki --skip-llm
rent-scraper scrape --city helsinki --max-listings 20 --skip-llm

# Just oikotie
rent-scraper scrape --city helsinki --sites oikotie --skip-llm

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
- `src/amsterdam_rent_scraper/scrapers/vuokraovi.py` - Blocked, disabled

## Technical Notes

### Oikotie Scraper Details
- Uses AngularJS (not Angular/React)
- Listings load dynamically, needs networkidle wait
- Uses absolute URLs in href attributes
- Listing URL pattern: `https://asunnot.oikotie.fi/vuokra-asunnot/{city}/{listing_id}`
- Rental search uses `vuokra-asunnot` path (vs `myytavat-asunnot` for sales)
- Location filter uses encoded location IDs: `[1656,4,"Helsinki"]`, `[1549,4,"Espoo"]`, `[1643,4,"Vantaa"]`
- Price filter: `price[min]=800&price[max]=1800` (URL encoded)

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
- Helsinki: IN PROGRESS (2 working scrapers - SATO, Oikotie)
