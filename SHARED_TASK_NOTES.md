# Multi-City Rent Scraper - Task Notes

## Current State: HELSINKI MODE WORKING - 4 SCRAPERS

Helsinki now has 4 working scrapers. The pipeline is fully functional.

### What Works
- `rent-scraper scrape --city helsinki` - All 4 scrapers working
- City-specific database: `output/helsinki_listings.db`
- City-specific exports: `output/helsinki_rentals.html`, `output/helsinki_rentals.xlsx`
- HSL transit routing calculating proper commute times to Keilasatama 5, Espoo
- Helsinki neighborhood quality scores (26 districts)
- Price/surface/room filtering all working correctly

### Working Helsinki Scrapers
1. **SATO** (`sato`) - Major Finnish rental company. Next.js site, works with Playwright.
2. **Oikotie** (`oikotie`) - Largest Finnish housing site. AngularJS site, works with Playwright.
3. **LUMO** (`lumo`) - Kojamo/Lumo apartments (~39,000 units across Finland). React/Redux site.
4. **TA** (`ta`) - **NEW** TA-Asunnot with 5,000+ apartments. WordPress site with server-rendered HTML. Extracts data from Findkit JSON + HTML patterns.

### Blocked/Disabled Scrapers
1. **Vuokraovi** (`vuokraovi`) - Blocks headless browsers completely. Disabled.

## Next Steps: MORE HELSINKI SCRAPERS

Potential sites to implement (in priority order):
1. **A-Kruunu** (a-kruunu.fi) - Affordable rentals in Helsinki metro area. Has external search at `a-kruunu-markkinointihaku.etampuuri.fi`.
2. **Retta Management** (vuokraus.rettamanagement.fi) - Helsinki rentals, some with first month free.
3. **forenom.com** - Furnished/temporary rentals. Blocked with 403.
4. **housinganywhere.com** - Already have scraper for Amsterdam but it's disabled (blocks headless browsers).

### Research Notes

**Etuovi.com:**
- Does NOT have rental listings - only sales (myytävät asunnot)
- Rental listings redirect to vuokraovi.com (same parent company)
- Skip this site for rentals

**TA.fi Implementation Notes:**
- WordPress site with custom "apartment" post type
- Listings page: `/asunnot/vuokra-asunto/helsinki/`
- Detail page: `/asunnot/etsi-asuntoa/{id}-{address}-{district}-{city}-vuokra-{id}/`
- Embeds Findkit JSON in `<script id='findkit'>` with apartment metadata (area, room type, postal code, district)
- Price found in `.SinglePage__SubTitle` (format: "837,93 €/kk")
- Features encoded in HTML classes: `additional-hope-hissi`, `additional-hope-parveke`, etc.
- "Lataa lisää" (Load more) button for pagination

## CLI Quick Reference
```bash
# Helsinki with all working scrapers
rent-scraper scrape --city helsinki --skip-llm
rent-scraper scrape --city helsinki --max-listings 20 --skip-llm

# Just ta
rent-scraper scrape --city helsinki --sites ta --skip-llm

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
- Helsinki: IN PROGRESS (4 working scrapers - SATO, Oikotie, LUMO, TA)

### Recent Changes
- Added TA-Asunnot scraper (ta.fi) with Findkit JSON extraction
