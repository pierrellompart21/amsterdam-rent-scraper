# Multi-City Rent Scraper - Task Notes

## Current State: STEALTH MODE COMPLETE

Stealth mode implementation is complete. The feature requires Google Chrome to be installed.

### Stealth Mode Usage

```bash
# Install stealth package (if not already installed)
pip install undetected-chromedriver

# IMPORTANT: Stealth mode requires Google Chrome browser to be installed
# On macOS: brew install --cask google-chrome
# On Ubuntu: sudo apt install google-chrome-stable

# Use --stealth flag
rent-scraper scrape --city amsterdam --stealth --sites funda --skip-llm --max-listings 5
rent-scraper scrape --city helsinki --stealth --sites vuokraovi --skip-llm --max-listings 5
```

### Implementation Files
- `src/amsterdam_rent_scraper/utils/stealth_browser.py` - StealthBrowser wrapper for undetected-chromedriver
- `src/amsterdam_rent_scraper/scrapers/stealth_base.py` - StealthBaseScraper base class
- `src/amsterdam_rent_scraper/scrapers/funda_stealth.py` - Stealth scraper for funda.nl
- `src/amsterdam_rent_scraper/scrapers/vuokraovi_stealth.py` - Stealth scraper for vuokraovi.com

### Testing Status
- ✅ All modules import correctly
- ✅ Normal scraping works without --stealth flag
- ✅ CLI shows helpful error message if Chrome is not installed
- ⚠️ Actual bot-detection bypass NOT tested (requires Chrome installed on test machine)

### Regular Scrapers (unchanged)
- Amsterdam (9): pararius, huurwoningen, wonen123, huurstunt, kamernet, iamexpat, rotsvast, expathousingnetwork, huure
- Helsinki (8): sato, oikotie, lumo, ta, retta, avara, keva, ovv

## CLI Quick Reference
```bash
# Normal scraping
rent-scraper scrape --city amsterdam --skip-llm
rent-scraper scrape --city helsinki --skip-llm

# Stealth mode (requires Chrome + pip install undetected-chromedriver)
rent-scraper scrape --city amsterdam --stealth --sites funda --skip-llm
rent-scraper scrape --city helsinki --stealth --sites vuokraovi --skip-llm

# Database info
rent-scraper db-info --city helsinki
rent-scraper export --city helsinki --format html
```
