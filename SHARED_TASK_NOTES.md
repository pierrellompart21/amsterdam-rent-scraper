# Multi-City Rent Scraper - Task Notes

## Current State: Stockholm City Added

Stockholm has been added as a new city option with 10 rental site scrapers.

### Stockholm Configuration
- Work Address: Vasagatan 12, 111 20 Stockholm, Sweden
- Price Range: 11,500 - 23,000 SEK (~1,000 - 2,000 EUR)
- Transit API: transitous
- 10 rental site scrapers (all JS-based, using Playwright)

### Stockholm Scrapers
All scrapers are placeholder implementations that need real-world testing:
- blocket, qasa, samtrygg, homeq, bostadsportalen
- hyresbostad, bovision, bostad_direkt, hemavi, renthia

### Stockholm Neighborhoods (26 areas)
Central: norrmalm, östermalm, södermalm, vasastan, kungsholmen, gamla stan, djurgården
South: hammarby sjöstad, gärdet, hjorthagen, liljeholmen, hornstull
Other: fridhemsplan, odenplan, sankt eriksplan
Suburbs: solna, sundbyberg, nacka, lidingö, danderyd, järfälla, sollentuna, huddinge, bromma, täby, upplands väsby

### Next Steps for Stockholm
1. Test each scraper against real sites to verify URL patterns and selectors work
2. Refine HTML parsing selectors based on actual site structure
3. Some sites may block headless browsers - may need stealth mode scrapers

## CLI Quick Reference
```bash
# Normal scraping
rent-scraper scrape --city amsterdam --skip-llm
rent-scraper scrape --city helsinki --skip-llm
rent-scraper scrape --city stockholm --skip-llm

# Test Stockholm with a single site
rent-scraper scrape --city stockholm --sites blocket --skip-llm --max-listings 5

# Stealth mode (requires Chrome + pip install undetected-chromedriver)
rent-scraper scrape --city amsterdam --stealth --sites funda --skip-llm
rent-scraper scrape --city helsinki --stealth --sites vuokraovi --skip-llm

# Database info
rent-scraper db-info --city stockholm
rent-scraper export --city stockholm --format html
```

## Regular Scrapers by City
- Amsterdam (9): pararius, huurwoningen, 123wonen, huurstunt, kamernet, iamexpat, rotsvast, expathousingnetwork, huure
- Helsinki (8): sato, oikotie, lumo, ta, retta, avara, keva, ovv
- Stockholm (10): blocket, qasa, samtrygg, homeq, bostadsportalen, hyresbostad, bovision, bostad_direkt, hemavi, renthia
