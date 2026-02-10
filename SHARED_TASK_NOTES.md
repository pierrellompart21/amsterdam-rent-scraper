# Multi-City Rent Scraper - Task Notes

## Current State: Stockholm City Added

Stockholm has been added as the third supported city. All configuration, neighborhoods, and placeholder scrapers are implemented.

### Stockholm Configuration
- Work address: Vasagatan 12, 111 20 Stockholm, Sweden
- Price range: 11,500 - 23,000 SEK (approximately 1,000 - 2,000 EUR)
- Currency: SEK (converted to EUR in scrapers)
- Transit API: transitous

### Stockholm Scrapers (10)
All scrapers inherit from PlaywrightBaseScraper with Swedish locale:
- blocket, qasa, samtrygg, homeq, bostadsportalen
- hyresbostad, bovision, bostad_direkt, hemavi, renthia

**Note**: Scrapers are placeholder implementations with basic structure. They will need tuning based on actual site HTML when tested.

### Stockholm Areas (12)
stockholm, solna, sundbyberg, nacka, lidingö, danderyd, järfälla, sollentuna, huddinge, bromma, täby, upplands väsby

### Stockholm Neighborhoods (26)
Central: norrmalm, östermalm, södermalm, vasastan, kungsholmen, gamla stan, djurgården
Other: hammarby sjöstad, gärdet, hjorthagen, liljeholmen, hornstull, fridhemsplan, odenplan, sankt eriksplan
Suburbs: solna, sundbyberg, nacka, lidingö, danderyd, järfälla, sollentuna, huddinge, bromma, täby, upplands väsby

## CLI Quick Reference
```bash
# Normal scraping
rent-scraper scrape --city amsterdam --skip-llm
rent-scraper scrape --city helsinki --skip-llm
rent-scraper scrape --city stockholm --skip-llm

# Stealth mode (requires Chrome + pip install undetected-chromedriver)
rent-scraper scrape --city amsterdam --stealth --sites funda --skip-llm
rent-scraper scrape --city helsinki --stealth --sites vuokraovi --skip-llm

# Database info
rent-scraper db-info --city stockholm
rent-scraper export --city stockholm --format html
```

## Next Steps for Stockholm
1. Test scrapers against actual Swedish rental sites
2. Adjust HTML selectors based on actual site structure
3. Add stealth scrapers if sites block headless browsers
4. Fine-tune Swedish price/room regex patterns based on real listings

## Regular Scrapers Summary
- Amsterdam (9): pararius, huurwoningen, 123wonen, huurstunt, kamernet, iamexpat, rotsvast, expathousingnetwork, huure
- Helsinki (8): sato, oikotie, lumo, ta, retta, avara, keva, ovv
- Stockholm (10): blocket, qasa, samtrygg, homeq, bostadsportalen, hyresbostad, bovision, bostad_direkt, hemavi, renthia
