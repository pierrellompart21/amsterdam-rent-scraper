# Multi-City Rent Scraper - Task Notes

## Current State: HELSINKI MODE WORKING

The first Helsinki scraper (SATO) is now working. The pipeline is functional for Helsinki.

### What Works
- `rent-scraper scrape --city helsinki --sites sato` - SATO scraper working
- City-specific database: `output/helsinki_listings.db`
- City-specific exports: `output/helsinki_rentals.html`, `output/helsinki_rentals.xlsx`
- HSL transit routing calculating proper commute times to Keilasatama 5, Espoo
- Helsinki neighborhood quality scores (26 districts)
- Price filtering, geocoding, all pipeline stages

### Working Helsinki Scrapers
1. **SATO** (`sato`) - Major Finnish rental company. Works well with Playwright. ~27 listings available.

### Blocked/Disabled Scrapers
1. **Vuokraovi** (`vuokraovi`) - Blocks headless browsers completely. Returns "Enable JavaScript" even with Playwright. Disabled.

## Next Steps: MORE HELSINKI SCRAPERS

Priority order for implementation:
1. **oikotie.fi** - Largest Finnish housing site. Complex JS, may need special handling. Reference: finscraper project has working code.
2. **etuovi.com** - Finnish housing marketplace (same company as vuokraovi)
3. **lumo.fi** - Kojamo/Lumo rentals. React SPA, navigation may be challenging.

### Research Notes

**Oikotie.fi:**
- Uses Angular.js
- API requires authentication (401 errors on direct API calls)
- finscraper project has working Selenium-based scraper for sales listings
- URL pattern: `https://asunnot.oikotie.fi/vuokra-asunnot?pagination=X`
- Listing cards: `//div[contains(@class, "cards-v2__card")]`
- May need to adapt the finscraper approach for rental listings

**Vuokraovi/Etuovi:**
- Same parent company, likely same anti-bot measures
- React/Material-UI frontend
- Strong headless browser detection
- Would need residential proxies or similar to bypass

**LUMO:**
- React Redux SPA
- Apartment cards don't have direct links - uses React Router
- May need to interact with cards via Playwright clicks

## CLI Quick Reference
```bash
# Helsinki with working scrapers
rent-scraper scrape --city helsinki --sites sato --skip-llm
rent-scraper scrape --city helsinki --max-listings 20 --skip-llm

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
- Helsinki: IN PROGRESS (1 working scraper - SATO)
