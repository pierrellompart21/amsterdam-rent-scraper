# Multi-City Rent Scraper - Task Notes

## Current State: Stockholm Scrapers In Progress

Stockholm is the third supported city. Scrapers are being expanded with priority Swedish rental sites.

### Stockholm Configuration
- Work address: Vasagatan 12, 111 20 Stockholm, Sweden
- Price range: 10,000 - 25,000 SEK
- Currency: SEK (converted to EUR in scrapers at ~11.5 SEK/EUR)
- Transit API: transitous

### Stockholm Scrapers (11)
**Working scrapers tested with real data:**
- heimstaden - API-based, intercepts Vue.js API calls. Tested: 435 listings, 16 Stockholm matches in price range. Rich data including coordinates, amenities.

**Existing scrapers (need testing/tuning):**
- blocket, qasa, samtrygg, homeq, bostadsportalen
- hyresbostad, bovision, bostad_direkt, hemavi, renthia

### Priority Sites Research Summary
From the goal's priority list:
- **hemnet.se** - Primarily for property SALES, not rentals. Skip.
- **rikshem.se** - Routes Stockholm apartments through Bostadsförmedlingen (queue system). Direct scraping not useful.
- **heimstaden.com** - DONE. Uses mitt.heimstaden.com with Vue.js + API
- **wallenstam.se** - Queue-based, Stockholm via Bostadsförmedlingen. Limited direct listings (mostly new construction)
- **victoriapark.se** - Stockholm via Bostadsförmedlingen. Not suitable for direct scraping.
- **stena.se** - Stockholm via Bostadsförmedlingen. Queue-based.
- **akelius.se** - Queue-based system without time-based priority. Portal at akelius.se/sv/search
- **sfrental.se** - Not found as a distinct site. May be defunct or different name.

### Next Priority Sites to Implement
Sites with direct listing access (not queue-only):
1. **akelius.se** - Has search portal, worth implementing
2. **wallenstam.se** - Has some direct listings for new construction

## CLI Quick Reference
```bash
# Test specific scraper
rent-scraper scrape --city stockholm --sites heimstaden --skip-llm

# Full Stockholm scrape
rent-scraper scrape --city stockholm --skip-llm

# Database info
rent-scraper db-info --city stockholm
rent-scraper export --city stockholm --format html
```

## Regular Scrapers Summary
- Amsterdam (9): pararius, huurwoningen, 123wonen, huurstunt, kamernet, iamexpat, rotsvast, expathousingnetwork, huure
- Helsinki (8): sato, oikotie, lumo, ta, retta, avara, keva, ovv
- Stockholm (11): blocket, qasa, samtrygg, homeq, bostadsportalen, hyresbostad, bovision, bostad_direkt, hemavi, renthia, heimstaden
