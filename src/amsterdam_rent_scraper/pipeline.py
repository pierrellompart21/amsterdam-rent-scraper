"""Main pipeline that orchestrates scraping, LLM extraction, and export."""

import importlib
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
    MofNCompleteColumn,
)
from rich.panel import Panel
from rich.table import Table

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
    max_listings_per_site: Optional[int] = None,
    apartments_only: bool = False,
    min_surface: Optional[int] = None,
    min_rooms: Optional[int] = None,
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

    # Display config summary
    config_table = Table(show_header=False, box=None, padding=(0, 2))
    config_table.add_column("Key", style="dim")
    config_table.add_column("Value", style="bold")

    mode_str = f"CUSTOM ({max_listings_per_site}/site)" if max_listings_per_site else ("TEST (3/site)" if test_mode else "FULL")
    config_table.add_row("Mode", mode_str)
    config_table.add_row("Sites", ", ".join(s.name for s in sites))
    config_table.add_row("Price", f"EUR {min_price} - {max_price}")
    if min_surface:
        config_table.add_row("Min Surface", f"{min_surface}m²")
    if min_rooms:
        config_table.add_row("Min Rooms", str(min_rooms))
    if apartments_only:
        config_table.add_row("Filter", "Apartments only")
    config_table.add_row("Output", str(output_dir))

    console.print(Panel(config_table, title="[bold]Amsterdam Rent Scraper[/]", border_style="cyan"))

    all_listings = []
    site_results = {}

    # Progress columns for main progress bar
    progress_columns = [
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
    ]

    # Run scrapers with progress tracking
    with Progress(*progress_columns, console=console) as progress:
        sites_task = progress.add_task(
            f"[cyan]Scraping {len(sites)} sites...",
            total=len(sites)
        )

        for site in sites:
            progress.update(sites_task, description=f"[cyan]{site.name.upper()}")

            try:
                scraper_class = load_scraper_class(site.scraper_class)
                scraper = scraper_class(
                    min_price=min_price,
                    max_price=max_price,
                    test_mode=test_mode,
                    max_listings=max_listings_per_site,
                )
                listings = scraper.scrape_all()
                all_listings.extend(listings)
                site_results[site.name] = len(listings)
            except ImportError as e:
                console.print(f"[yellow]⚠ Scraper not implemented: {site.name} ({e})[/]")
                site_results[site.name] = 0
            except Exception as e:
                console.print(f"[red]✗ Error scraping {site.name}: {e}[/]")
                site_results[site.name] = 0

            progress.advance(sites_task)

    # Show summary table of scraped listings per site
    if site_results:
        summary_table = Table(title="Scraping Results", box=None)
        summary_table.add_column("Site", style="cyan")
        summary_table.add_column("Listings", justify="right", style="green")
        for site_name, count in site_results.items():
            summary_table.add_row(site_name, str(count))
        summary_table.add_row("─" * 15, "─" * 8, style="dim")
        summary_table.add_row("[bold]Total[/]", f"[bold]{len(all_listings)}[/]")
        console.print(summary_table)

    if not all_listings:
        console.print("[yellow]No listings scraped.[/]")
        return []

    console.print(f"\n[bold]Total raw listings: {len(all_listings)}[/]")

    # LLM enrichment (or regex fallback)
    if not skip_llm:
        extractor = OllamaExtractor()

        if extractor.is_available():
            with Progress(*progress_columns, console=console) as progress:
                task = progress.add_task("[cyan]LLM extraction...", total=len(all_listings))
                for listing in all_listings:
                    raw_path = listing.get("raw_page_path")
                    if raw_path:
                        listing.update(extractor.enrich_listing(listing, raw_path))
                    progress.advance(task)
        else:
            console.print("[yellow]⚠ Ollama not available, using regex fallback[/]")
            with Progress(*progress_columns, console=console) as progress:
                task = progress.add_task("[cyan]Regex extraction...", total=len(all_listings))
                for listing in all_listings:
                    raw_path = listing.get("raw_page_path")
                    if raw_path:
                        try:
                            with open(raw_path, "r", encoding="utf-8") as f:
                                html = f.read()
                            listing.update(regex_extract_from_html(html, listing))
                        except Exception:
                            pass
                    progress.advance(task)
    else:
        console.print("[dim]Skipping LLM (--skip-llm), using regex fallback[/]")
        with Progress(*progress_columns, console=console) as progress:
            task = progress.add_task("[cyan]Regex extraction...", total=len(all_listings))
            for listing in all_listings:
                raw_path = listing.get("raw_page_path")
                if raw_path:
                    try:
                        with open(raw_path, "r", encoding="utf-8") as f:
                            html = f.read()
                        listing.update(regex_extract_from_html(html, listing))
                    except Exception:
                        pass
                progress.advance(task)

    # Post-extraction price filtering
    # Many sites don't respect URL price filters, so we filter after extraction
    pre_filter_count = len(all_listings)
    all_listings = [
        listing for listing in all_listings
        if listing.get("price_eur") is None  # Keep listings without price (for review)
        or (min_price <= listing.get("price_eur", 0) <= max_price)
    ]
    price_filtered = pre_filter_count - len(all_listings)
    if price_filtered > 0:
        console.print(f"[yellow]Filtered {price_filtered} listings outside price range EUR {min_price}-{max_price}[/]")

    # Filter out rooms/shared housing if requested
    if apartments_only:
        room_types = {"room", "kamer", "shared"}
        pre_filter_count = len(all_listings)
        filtered_listings = []
        for listing in all_listings:
            property_type = (listing.get("property_type") or "").lower()
            title = (listing.get("title") or "").lower()
            url = (listing.get("url") or "").lower()

            # Check if it's a room listing
            is_room = (
                property_type in room_types
                or "/kamer-" in url
                or "kamer " in title
                or "shared" in title
            )
            if not is_room:
                filtered_listings.append(listing)

        all_listings = filtered_listings
        rooms_filtered = pre_filter_count - len(all_listings)
        if rooms_filtered > 0:
            console.print(f"[yellow]Filtered {rooms_filtered} room/shared listings (apartments only mode)[/]")

    # Surface area filter
    if min_surface:
        pre_filter_count = len(all_listings)
        all_listings = [
            listing for listing in all_listings
            if listing.get("surface_sqm") is None  # Keep listings without surface (for review)
            or listing.get("surface_sqm", 0) >= min_surface
        ]
        surface_filtered = pre_filter_count - len(all_listings)
        if surface_filtered > 0:
            console.print(f"[yellow]Filtered {surface_filtered} listings below {min_surface}m² surface[/]")

    # Rooms filter
    if min_rooms:
        pre_filter_count = len(all_listings)
        all_listings = [
            listing for listing in all_listings
            if listing.get("bedrooms") is None  # Keep listings without room count (for review)
            or listing.get("bedrooms", 0) >= min_rooms
        ]
        rooms_filtered = pre_filter_count - len(all_listings)
        if rooms_filtered > 0:
            console.print(f"[yellow]Filtered {rooms_filtered} listings below {min_rooms} rooms[/]")

    # Geographic enrichment
    with Progress(*progress_columns, console=console) as progress:
        task = progress.add_task("[cyan]Geocoding addresses...", total=len(all_listings))
        for listing in all_listings:
            enrich_listing_with_geo(listing)
            progress.advance(task)

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
