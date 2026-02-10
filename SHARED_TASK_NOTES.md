# Multi-City Rent Scraper - Task Notes

## Current State: Stockholm City Added

Stockholm has been added as the third supported city with 10 rental site scrapers.

### Stockholm Configuration
- Work address: Vasagatan 12, 111 20 Stockholm, Sweden
- Coordinates: 59.3320, 18.0590
- Price range: 12,000-25,000 SEK (approx 1,000-2,000 EUR)
- Transit API: transitous
- 10 scrapers: blocket, qasa, samtrygg, homeq, bostadsportalen, hyresbostad, bovision, bostad_direkt, hemavi, renthia

### Stockholm Scrapers Status
All 10 scrapers are created as functional placeholders. They:
- Inherit from PlaywrightBaseScraper (all Swedish sites are JS-heavy)
- Have search URL templates with price filters
- Parse Swedish rental formats (SEK prices, "rum" for rooms, Swedish postal codes)
- Include TODO comments where site-specific HTML selectors need verification

**Next steps for Stockholm scrapers:**
1. Test each scraper against the live site
2. Update CSS selectors in `get_listing_urls()` based on actual HTML structure
3. Verify price/room/surface extraction patterns work
4. Some sites may require authentication or subscription - document limitations

### File Changes Made
- `src/amsterdam_rent_scraper/config/settings.py` - Added Stockholm city config, area locations, location centers, and RentalSite entries
- `src/amsterdam_rent_scraper/utils/neighborhoods.py` - Added 25 Stockholm neighborhoods with scores, aliases, and postal code detection
- `src/amsterdam_rent_scraper/pipeline.py` - Updated to use STOCKHOLM_AREA_LOCATIONS for Stockholm
- `src/amsterdam_rent_scraper/scrapers/` - Created 10 new scraper files (blocket.py, qasa.py, samtrygg.py, homeq.py, bostadsportalen.py, hyresbostad.py, bovision.py, bostad_direkt.py, hemavi.py, renthia.py)

### Verified Working
- `get_city_config('stockholm')` returns correct config
- All 10 Stockholm scrapers import successfully
- Neighborhood identification works for Stockholm
- CLI shows Stockholm as available city option

## CLI Quick Reference
```bash
# Stockholm scraping (new)
rent-scraper scrape --city stockholm --skip-llm --test-run
rent-scraper scrape --city stockholm --sites blocket,qasa --skip-llm --max-listings 5
rent-scraper db-info --city stockholm
rent-scraper export --city stockholm --format html

# Existing cities
rent-scraper scrape --city amsterdam --skip-llm
rent-scraper scrape --city helsinki --skip-llm

# Stealth mode (requires Chrome + pip install undetected-chromedriver)
rent-scraper scrape --city amsterdam --stealth --sites funda --skip-llm
rent-scraper scrape --city helsinki --stealth --sites vuokraovi --skip-llm
```

### Supported Cities Summary
| City | Country | Scrapers | Currency | Notes |
|------|---------|----------|----------|-------|
| Amsterdam | Netherlands | 9 | EUR | + Funda (stealth) |
| Helsinki | Finland | 8 | EUR | + Vuokraovi (stealth) |
| Stockholm | Sweden | 10 | SEK | New - scrapers need testing |

### Notes on Swedish Sites
- Prices are in SEK (1 EUR ≈ 11.5 SEK)
- Room format: "X rum" or "X rok" (rum och kök)
- Postal codes: 5 digits (e.g., "111 20")
- Most sites require JavaScript rendering
- Blocket and Qasa are the most popular platforms
