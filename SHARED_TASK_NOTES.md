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
- **OSRM Commute Routing**: Real bike and driving times via OSRM API (free, no key needed)
  - `get_osrm_route()` and `get_commute_routes()` in `utils/geo.py`
  - Returns actual routed distance/time + route coordinates for map display
  - Rate-limited to 1 req/sec to respect free service
- Added `commute_time_driving_min` and `bike_route_coords` fields to model
- Updated HTML report: bike/car time columns, max bike commute filter, route polyline on marker click
- Updated Excel export with driving time column
- Fixed work coordinates to (52.3027, 4.8557) for Stroombaan 4, Amstelveen

## CLI Options
```bash
# Install
pip install -e .
playwright install chromium

# Quick test (3 listings per site, limited pages)
rent-scraper --test-run --sites pararius --skip-llm

# With surface/rooms filters
rent-scraper --max-listings 10 --sites pararius --skip-llm --min-surface 60 --min-rooms 2

# Full run - scrapes ALL available listings (paginates until no more results)
rent-scraper --sites pararius,huurwoningen --skip-llm
```

## Next Priority Tasks
1. **Neighborhood quality scores** - Hardcode Amsterdam district ratings (safety, green_space, amenities, etc.)
2. **SQLite database** - Store listings with deduplication by URL, add `export --format excel/html` command
3. **HTML report improvements** - Cards layout, price range slider, colored markers, modern CSS
4. **More rental sites** - Search for vesteda.com, holland2stay.com, iamexpat.nl/housing
5. **README.md** - Setup instructions, usage examples, architecture

## Key Files
- `src/amsterdam_rent_scraper/cli/main.py` - CLI with --apartments-only, --min-surface, --min-rooms
- `src/amsterdam_rent_scraper/pipeline.py` - Post-extraction filtering, rich progress bars
- `src/amsterdam_rent_scraper/utils/geo.py` - OSRM routing, geocoding, commute calculations
- `src/amsterdam_rent_scraper/models/listing.py` - RentalListing with commute fields
- `src/amsterdam_rent_scraper/export/html_report.py` - Interactive HTML with route display

## Technical Notes
- OSRM API: `http://router.project-osrm.org/route/v1/{cycling|driving}/lon1,lat1;lon2,lat2?overview=full&geometries=geojson`
- Transit times still use heuristic (OSRM doesn't have transit routing)
- Route coords stored as `[[lon,lat], ...]` (OSRM format), converted to `[lat,lon]` for Leaflet display
- Target: Stroombaan 4, 1181 VX Amstelveen (52.3027, 4.8557)
- Price range: EUR 1000-2000, Min surface: 60m2, Min rooms: 2
