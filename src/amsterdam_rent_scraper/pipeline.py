"""Main pipeline that orchestrates scraping, LLM extraction, and export."""

import importlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from tqdm import tqdm

from amsterdam_rent_scraper.config.settings import (
    MIN_PRICE,
    MAX_PRICE,
    OUTPUT_DIR,
    get_enabled_sites,
)
from amsterdam_rent_scraper.export.excel import export_to_excel
from amsterdam_rent_scraper.export.html_report import export_to_html
from amsterdam_rent_scraper.llm.extractor import OllamaExtractor
from amsterdam_rent_scraper.llm.regex_fallback import regex_extract_from_html
from amsterdam_rent_scraper.models.listing import RentalListing
from amsterdam_rent_scraper.utils.geo import enrich_listing_with_geo

console = Console()


def load_scraper_class(dotted_path: str):
    """Dynamically load a scraper class from its dotted path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def run_pipeline(
    test_mode: bool = False,
    site_filter: Optional[list[str]] = None,
    skip_llm: bool = False,
    output_dir: Path = None,
    min_price: int = None,
    max_price: int = None,
) -> list[dict]:
    """
    Run the full scraping pipeline.

    1. Get enabled sites (filtered if specified)
    2. For each site, run the scraper
    3. Optionally enrich with LLM extraction
    4. Add geographic data
    5. Export to Excel and HTML
    """
    output_dir = Path(output_dir or OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    min_price = min_price or MIN_PRICE
    max_price = max_price or MAX_PRICE

    sites = get_enabled_sites(site_filter)
    if not sites:
        console.print("[red]No sites to scrape. Check your --sites filter.[/]")
        return []

    console.print(f"\n[bold]Starting scrape pipeline[/]")
    console.print(f"  Mode: {'TEST (3 listings/site)' if test_mode else 'FULL'}")
    console.print(f"  Sites: {', '.join(s.name for s in sites)}")
    console.print(f"  Price range: EUR {min_price} - {max_price}")
    console.print("")

    all_listings = []

    # Run scrapers
    for site in sites:
        console.print(f"\n[bold cyan]>>> {site.name.upper()}[/]")

        try:
            scraper_class = load_scraper_class(site.scraper_class)
            scraper = scraper_class(
                min_price=min_price, max_price=max_price, test_mode=test_mode
            )
            listings = scraper.scrape_all()
            all_listings.extend(listings)
        except ImportError as e:
            console.print(f"[yellow]Scraper not implemented yet: {site.name} ({e})[/]")
        except Exception as e:
            console.print(f"[red]Error scraping {site.name}: {e}[/]")

    if not all_listings:
        console.print("[yellow]No listings scraped.[/]")
        return []

    console.print(f"\n[bold]Total raw listings: {len(all_listings)}[/]")

    # LLM enrichment (or regex fallback)
    if not skip_llm:
        console.print("\n[bold cyan]Running LLM extraction...[/]")
        extractor = OllamaExtractor()

        if extractor.is_available():
            for listing in tqdm(all_listings, desc="LLM extraction"):
                raw_path = listing.get("raw_page_path")
                if raw_path:
                    listing.update(extractor.enrich_listing(listing, raw_path))
        else:
            console.print(
                "[yellow]Skipping LLM extraction (Ollama not available)[/]"
            )
            # Use regex fallback instead
            console.print("[cyan]Using regex fallback extraction...[/]")
            for listing in tqdm(all_listings, desc="Regex extraction"):
                raw_path = listing.get("raw_page_path")
                if raw_path:
                    try:
                        with open(raw_path, "r", encoding="utf-8") as f:
                            html = f.read()
                        listing.update(regex_extract_from_html(html, listing))
                    except Exception:
                        pass
    else:
        console.print("[dim]Skipping LLM extraction (--skip-llm)[/]")
        # Still apply regex fallback for basic field extraction
        console.print("[cyan]Using regex fallback extraction...[/]")
        for listing in tqdm(all_listings, desc="Regex extraction"):
            raw_path = listing.get("raw_page_path")
            if raw_path:
                try:
                    with open(raw_path, "r", encoding="utf-8") as f:
                        html = f.read()
                    listing.update(regex_extract_from_html(html, listing))
                except Exception:
                    pass

    # Geographic enrichment
    console.print("\n[bold cyan]Adding geographic data...[/]")
    for listing in tqdm(all_listings, desc="Geocoding"):
        enrich_listing_with_geo(listing)

    # Add scraped timestamp
    now = datetime.now()
    for listing in all_listings:
        listing["scraped_at"] = now

    # Export
    console.print("\n[bold cyan]Exporting results...[/]")
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    excel_path = export_to_excel(
        all_listings, output_dir, f"amsterdam_rentals_{timestamp}.xlsx"
    )
    html_path = export_to_html(
        all_listings, output_dir, f"amsterdam_rentals_{timestamp}.html"
    )

    # Also export latest versions without timestamp
    export_to_excel(all_listings, output_dir, "amsterdam_rentals.xlsx")
    export_to_html(all_listings, output_dir, "amsterdam_rentals.html")

    console.print("\n[bold green]Pipeline complete![/]")
    console.print(f"  Listings: {len(all_listings)}")
    console.print(f"  Excel: {excel_path}")
    console.print(f"  HTML: {html_path}")

    return all_listings
