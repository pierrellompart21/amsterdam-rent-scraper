# Multi-City Rent Scraper - Task Notes

## Current State: HELSINKI MODE WORKING - 8 SCRAPERS

Helsinki now has 8 working scrapers. The pipeline is fully functional.

### What Works
- `rent-scraper scrape --city helsinki` - All 8 scrapers working
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
5. **Retta** (`retta`) - Retta Management (~1,000 Helsinki area listings). Next.js site with __NEXT_DATA__.
6. **Avara** (`avara`) - Avara rental company (~7,000 apartments). Public JSON API at oma.avara.fi.
7. **Keva** (`keva`) - Keva pension fund apartments (~3,500 units). WordPress site with clean HTML - no JS rendering needed.
8. **OVV** (`ovv`) - **NEW** OVV Asuntopalvelut / Auroranlinna (City of Helsinki) ~6,000 apartments. WordPress AJAX with API interception - returns JSON directly from the admin-ajax.php endpoint.

### Blocked/Disabled Scrapers
1. **Vuokraovi** (`vuokraovi`) - Blocks headless browsers completely. Disabled.

## Next Steps: MORE HELSINKI SCRAPERS (if needed)

Most remaining sites are complex (WordPress AJAX without exposed endpoints) or blocked:

1. **M2-Kodit** (m2kodit.fi) - Part of Y-Säätiö, 11,500 ARA-subsidized apartments. WordPress with AJAX, no easy JSON endpoint.
2. **A-Kruunu** (a-kruunu.fi) - Affordable rentals. Uses external Knockout.js search at etampuuri.fi - complex to scrape.
3. **Forenom** (forenom.com) - Returns 403 - blocked.
4. **Asuntosäätiö** (asuntosaatio.fi) - WordPress with AJAX/React hybrid, complex dynamic loading.
5. **Kodisto** (kodisto.fi by Newsec) - Next.js but returned no listings in testing.

### Research Summary
- **Blok.ai** - For apartment sales only, not rentals. Skip.
- **Etuovi.com** - Redirects to Vuokraovi for rentals (blocked). Skip.
- **Heka** (City of Helsinki housing) - Lists on Oikotie (which we already scrape). Skip.
- **Kojamo/VVO** - Parent company of LUMO (already have scraper). Skip.
- **Hoas** - Student housing only. Not for general renters.

## CLI Quick Reference
```bash
# Helsinki with all working scrapers
rent-scraper scrape --city helsinki --skip-llm
rent-scraper scrape --city helsinki --max-listings 20 --skip-llm

# Fast scrapers (pure HTTP, no Playwright)
rent-scraper scrape --city helsinki --sites keva --skip-llm
rent-scraper scrape --city helsinki --sites avara --skip-llm

# OVV scraper (Playwright + API interception)
rent-scraper scrape --city helsinki --sites ovv --skip-llm

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
- `src/amsterdam_rent_scraper/scrapers/retta.py` - Working Retta scraper
- `src/amsterdam_rent_scraper/scrapers/avara.py` - Working Avara scraper (JSON API)
- `src/amsterdam_rent_scraper/scrapers/keva.py` - Working Keva scraper (HTML)
- `src/amsterdam_rent_scraper/scrapers/ovv.py` - Working OVV scraper (Playwright + API)
- `src/amsterdam_rent_scraper/scrapers/vuokraovi.py` - Blocked, disabled

## Technical Notes

### Finnish Site Considerations
- **Language**: Sites in Finnish. Key terms: vuokra (rent), asunto (apartment), huone (room), neliö (m²)
- **Postal codes**: 5 digits (00XXX = Helsinki, 01XXX = Vantaa, 02XXX = Espoo)
- **Price format**: "X €/kk" (euros per month), may have spaces in thousands, comma as decimal
- **Room format**: "3h+k" = 3 rooms + kitchen, "2h+kk" = 2 rooms + kitchenette
- **Room words**: yksiö (studio), kaksio (2 rooms), kolmio (3 rooms), neliö (4 rooms)
- **Sauna**: Very common in Finnish apartments, often abbreviated as "+s"

### OVV Scraper Notes
- OVV site uses WordPress with AJAX for dynamic listing loading
- The scraper intercepts the JSON response from `/wp-admin/admin-ajax.php`
- Action: `ovv_plugin_get_realties`, returns ~10 listings per page (no pagination exposed)
- City filter: "Helsinki" office gives best Helsinki results
- OVV/Auroranlinna primarily has affordable smaller apartments, so many may be filtered out by min_surface=40m² and min_rooms=2

### Helsinki Office Target
- Address: Keilasatama 5, 02150 Espoo, Finland
- Coordinates: (60.1756, 24.8271)
- Transit API: HSL Digitransit (working)

## Project Status
- Amsterdam: COMPLETE (9 working scrapers)
- Helsinki: IN PROGRESS (8 working scrapers - SATO, Oikotie, LUMO, TA, Retta, Avara, Keva, OVV)

### Recent Changes
- Added OVV scraper - intercepts WordPress AJAX API response
- Database now has 61 Helsinki listings across 8 scrapers
