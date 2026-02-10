# Multi-City Rent Scraper - Task Notes

## Current State: Stockholm Scrapers In Progress

Stockholm is the third supported city. Scrapers are being expanded with priority Swedish rental sites.

### Stockholm Configuration
- Work address: Vasagatan 12, 111 20 Stockholm, Sweden
- Price range: 10,000 - 25,000 SEK (~870-2175 EUR)
- Currency: SEK (converted to EUR in scrapers at ~11.5 SEK/EUR)
- Transit API: transitous

### Known Issue: Price Filtering
The pipeline filters on `price_eur` but Stockholm's config has SEK prices. When testing Stockholm scrapers, use EUR values with `--min-price` and `--max-price` (e.g., `--min-price 800 --max-price 2500`).

### Stockholm Scrapers (12)
**Working scrapers tested with real data:**
- heimstaden - API-based, intercepts Vue.js API calls. Tested: 435 listings, 16 Stockholm matches.
- rentumo - Server-rendered aggregator. Tested: 210 listings found, proper price/surface/geocoding extraction.

**Existing scrapers (need testing/tuning):**
- blocket, qasa, samtrygg, homeq, bostadsportalen
- hyresbostad, bovision, bostad_direkt, hemavi, renthia

### Priority Sites Research Summary
From the goal's priority list:
- **hemnet.se** - Primarily for property SALES, not rentals. Skip.
- **rikshem.se** - Routes Stockholm apartments through Bostadsförmedlingen (queue system). Skip.
- **heimstaden.com** - DONE. Uses mitt.heimstaden.com with Vue.js + API
- **rentumo.se** - DONE. Aggregator with 1300+ Stockholm listings. Server-rendered.
- **wallenstam.se** - Queue-based, limited direct listings. Skip for now.
- **victoriapark.se** - Stockholm via Bostadsförmedlingen. Skip.
- **stena.se** - Stockholm via Bostadsförmedlingen. Skip.
- **akelius.se** - Sold Swedish properties in 2021. No longer operates in Sweden.
- **sfrental.se** - Not found. May be defunct.

### Additional Sites Discovered
- **bostadsportal.se** - 200+ Stockholm listings (different from bostadsportalen)
- **homii.se** - 5700+ listings but uses AngularJS SPA, needs API exploration
- **bostadslistan.se** - 2000+ apartments but Cloudflare protected

## CLI Quick Reference
```bash
# Test specific scraper with EUR prices
rent-scraper scrape --city stockholm --sites rentumo --skip-llm --min-price 800 --max-price 2500

# Full Stockholm scrape
rent-scraper scrape --city stockholm --skip-llm

# Database info
rent-scraper db-info --city stockholm
rent-scraper export --city stockholm --format html
```

## Regular Scrapers Summary
- Amsterdam (9): pararius, huurwoningen, 123wonen, huurstunt, kamernet, iamexpat, rotsvast, expathousingnetwork, huure
- Helsinki (8): sato, oikotie, lumo, ta, retta, avara, keva, ovv
- Stockholm (12): blocket, qasa, samtrygg, homeq, bostadsportalen, hyresbostad, bovision, bostad_direkt, hemavi, renthia, heimstaden, rentumo
