# Multi-City Rent Scraper - Task Notes

## Current State: STEALTH MODE IMPLEMENTED

Stealth mode has been added as an opt-in feature for bypassing bot detection on blocked sites.

### Stealth Mode Feature (NEW)

Added `--stealth` flag to the CLI for scraping sites that block headless browsers.

**To use stealth mode:**
```bash
# Install stealth package first (not installed by default)
pip install undetected-chromedriver

# Then use --stealth flag
rent-scraper scrape --city amsterdam --stealth --sites funda --skip-llm --max-listings 5
rent-scraper scrape --city helsinki --stealth --sites vuokraovi --skip-llm --max-listings 5
```

**New files created:**
- `src/amsterdam_rent_scraper/utils/stealth_browser.py` - StealthBrowser wrapper for undetected-chromedriver
- `src/amsterdam_rent_scraper/scrapers/stealth_base.py` - StealthBaseScraper base class
- `src/amsterdam_rent_scraper/scrapers/funda_stealth.py` - Stealth scraper for funda.nl
- `src/amsterdam_rent_scraper/scrapers/vuokraovi_stealth.py` - Stealth scraper for vuokraovi.com

**Configuration in settings.py:**
- `STEALTH_SITES` dict maps site names to their stealth scraper classes
- Currently supports: funda (amsterdam), vuokraovi (helsinki)

**Testing status:**
- ✅ All modules import correctly
- ✅ Normal scraping still works without --stealth
- ✅ CLI shows --stealth option with helpful messages
- ⚠️ Actual stealth scraping NOT tested (requires `pip install undetected-chromedriver`)

### Next Steps (if continuing this feature)
1. Install undetected-chromedriver and test actual stealth scraping
2. Verify it can bypass funda.nl and vuokraovi.com bot detection
3. Fine-tune delays and human-like behavior if needed

### Regular Scrapers (still working)
- Amsterdam (9): pararius, huurwoningen, wonen123, huurstunt, kamernet, iamexpat, rotsvast, expathousingnetwork, huure
- Helsinki (8): sato, oikotie, lumo, ta, retta, avara, keva, ovv

## CLI Quick Reference
```bash
# Normal scraping
rent-scraper scrape --city amsterdam --skip-llm
rent-scraper scrape --city helsinki --skip-llm

# Stealth mode (requires pip install undetected-chromedriver)
rent-scraper scrape --city amsterdam --stealth --sites funda --skip-llm
rent-scraper scrape --city helsinki --stealth --sites vuokraovi --skip-llm

# Database info
rent-scraper db-info --city helsinki
rent-scraper export --city helsinki --format html
```
