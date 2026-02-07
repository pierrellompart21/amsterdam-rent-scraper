# Multi-City Rent Scraper - Task Notes

## Current State: HELSINKI MODE IN PROGRESS

The project has been refactored to support multiple cities. The core multi-city infrastructure is complete:

- **City configuration system** in `config/settings.py` with `CityConfig` dataclass
- **CLI `--city` flag** added to scrape, export, and db-info commands
- **Pipeline updated** to pass city parameter through all stages
- **Geo utilities updated** with per-city office location, transit routing (HSL API for Helsinki)
- **Neighborhoods updated** with Helsinki district data (26 areas: Kallio, Töölö, Tapiola, etc.)
- **HTML export updated** with city-specific title, map center, work location

### What Works
- `rent-scraper scrape --city amsterdam` - All 9 Amsterdam scrapers work
- City-specific database files: `amsterdam_listings.db`, `helsinki_listings.db`
- City-specific export files: `amsterdam_rentals.html`, `helsinki_rentals.html`
- HSL Digitransit API integration for Helsinki transit routing
- Helsinki neighborhood quality scores (26 districts)

### What's Missing
- **Helsinki scrapers** - None implemented yet! The `enabled_scrapers` list in Helsinki config is empty.

## Next Steps: IMPLEMENT HELSINKI SCRAPERS

Priority order for implementation:
1. **oikotie.fi** - Largest Finnish housing site (vuokra-asunnot section)
2. **vuokraovi.com** - Major Finnish rental portal
3. **etuovi.com** - Finnish housing marketplace
4. **blok.ai** - Modern Finnish rental platform
5. **lumo.fi** - Kojamo/Lumo rental apartments
6. **sato.fi** - SATO rental apartments

### Implementation Guide
For each Helsinki scraper:

1. Add RentalSite entry to `config/settings.py` (in HELSINKI section):
```python
RentalSite(
    name="oikotie",
    base_url="https://asunnot.oikotie.fi",
    search_url_template="...",
    scraper_class="amsterdam_rent_scraper.scrapers.oikotie.OikotieScraper",
    city="helsinki",  # IMPORTANT!
    needs_js=True,  # Most modern Finnish sites need Playwright
    notes="Largest Finnish housing site.",
),
```

2. Add scraper name to Helsinki `enabled_scrapers` in `CITIES["helsinki"]`:
```python
enabled_scrapers=["oikotie", "vuokraovi", ...],
```

3. Create scraper class (e.g., `scrapers/oikotie.py`) inheriting from `BaseScraper` or `PlaywrightBaseScraper`

4. Test with:
```bash
rent-scraper scrape --city helsinki --test-run --sites oikotie --skip-llm
```

### Finnish Site Considerations
- **Language**: Sites are in Finnish (suomi). Field names like "vuokra" (rent), "neliöt" (m²), "huoneet" (rooms)
- **Postal codes**: Finnish format is 5 digits (e.g., 00100 Helsinki, 02150 Espoo)
- **Currency**: EUR (same as Netherlands)
- **Most sites are JS-rendered**: Use Playwright with `domcontentloaded` wait strategy

## CLI Quick Reference
```bash
# Amsterdam (default)
rent-scraper scrape --test-run --sites pararius --skip-llm

# Helsinki
rent-scraper scrape --city helsinki --test-run --sites oikotie --skip-llm

# Export
rent-scraper export --city helsinki --format html

# DB stats
rent-scraper db-info --city helsinki
```

## Key Files
- `src/amsterdam_rent_scraper/config/settings.py` - City configs, CITIES dict, RentalSite entries
- `src/amsterdam_rent_scraper/cli/main.py` - CLI with --city flag
- `src/amsterdam_rent_scraper/pipeline.py` - Main orchestration (city-aware)
- `src/amsterdam_rent_scraper/utils/geo.py` - Routing (OSRM + Transitous/HSL)
- `src/amsterdam_rent_scraper/utils/neighborhoods.py` - Neighborhood data for both cities
- `src/amsterdam_rent_scraper/export/html_report.py` - HTML export (city-aware)

## Technical Notes

### HSL Digitransit API (Helsinki Transit)
- Endpoint: `https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql`
- Uses GraphQL for route planning
- Free API with public test key
- Falls back to Transitous if HSL fails (Transitous also covers Finland)

### Helsinki Office Target
- Address: Keilasatama 5, 02150 Espoo, Finland
- Coordinates: (60.1756, 24.8271)
- This is a common Espoo tech hub area (near Microsoft, Nokia)

### Helsinki Price/Size Defaults
- Price: 800-1800 EUR/month
- Min surface: 40 m²
- Min rooms: 2

## Project Status
- Amsterdam: COMPLETE (9 working scrapers)
- Helsinki: IN PROGRESS (multi-city infrastructure done, scrapers needed)
