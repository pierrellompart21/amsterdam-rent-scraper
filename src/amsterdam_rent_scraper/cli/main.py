"""CLI entry point for the multi-city rent scraper."""

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from amsterdam_rent_scraper.config.settings import CITIES, DEFAULT_CITY, STEALTH_SITES, get_city_config

app = typer.Typer(
    name="rent-scraper", help="Multi-city rental listing scraper + LLM extraction"
)
console = Console()


class ExportFormat(str, Enum):
    """Export format options."""
    excel = "excel"
    html = "html"
    both = "both"


@app.command()
def scrape(
    city: str = typer.Option(
        DEFAULT_CITY, "--city", "-c",
        help=f"City to scrape ({', '.join(CITIES.keys())})"
    ),
    test_run: bool = typer.Option(
        False, "--test-run", "-t", help="Scrape only 3 listings per site"
    ),
    full_run: bool = typer.Option(
        False, "--full-run", "-f", help="Scrape all listings from all sites"
    ),
    sites: list[str] = typer.Option(
        None, "--sites", "-s", help="Filter specific sites (e.g. pararius,huurwoningen)"
    ),
    max_listings: int = typer.Option(
        None, "--max-listings", "-n", help="Max listings per site (overrides --test-run limit)"
    ),
    min_price: int = typer.Option(
        None, "--min-price", help="Minimum rent in EUR (default: city-specific)"
    ),
    max_price: int = typer.Option(
        None, "--max-price", help="Maximum rent in EUR (default: city-specific)"
    ),
    output_dir: Path = typer.Option(
        Path("output"), "--output-dir", "-o", help="Output directory"
    ),
    skip_llm: bool = typer.Option(
        False, "--skip-llm", help="Skip LLM extraction (scrape only)"
    ),
    apartments_only: bool = typer.Option(
        False, "--apartments-only", "-a", help="Filter out rooms/shared housing"
    ),
    min_surface: int = typer.Option(
        None, "--min-surface", help="Minimum surface area in m² (default: city-specific)"
    ),
    min_rooms: int = typer.Option(
        None, "--min-rooms", help="Minimum number of rooms (default: city-specific)"
    ),
    ollama_model: str = typer.Option(
        "llama3", "--model", "-m", help="Ollama model name"
    ),
    resume: bool = typer.Option(
        False, "--resume", "-r", help="Resume from last checkpoint if available"
    ),
    stealth: bool = typer.Option(
        False, "--stealth", help="Use stealth mode for blocked sites (funda, vuokraovi)"
    ),
):
    """
    Scrape rental websites for apartment listings.

    Examples:
        rent-scraper scrape --city amsterdam --test-run
        rent-scraper scrape --city helsinki --sites oikotie,lumo
        rent-scraper scrape -c amsterdam -t --min-price 1200 --max-price 1800
        rent-scraper scrape --resume  # Resume a failed run
        rent-scraper scrape --city amsterdam --stealth --sites funda  # Stealth mode for blocked sites
        rent-scraper scrape --city helsinki --stealth --sites vuokraovi  # Stealth mode for vuokraovi
    """
    from amsterdam_rent_scraper.pipeline import run_pipeline

    # Get city configuration
    try:
        city_config = get_city_config(city)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)

    # Use city defaults if not specified
    min_price = min_price if min_price is not None else city_config.min_price
    max_price = max_price if max_price is not None else city_config.max_price
    min_surface = min_surface if min_surface is not None else city_config.min_surface
    min_rooms = min_rooms if min_rooms is not None else city_config.min_rooms

    site_filter = None
    if sites:
        # Handle both --sites funda --sites pararius AND --sites funda,pararius
        site_filter = []
        for s in sites:
            site_filter.extend(s.split(","))

    mode = "test" if test_run else "full"
    if resume:
        console.print(f"[bold]{city_config.name} Rent Scraper - resuming {mode} mode[/]")
    else:
        console.print(f"[bold]{city_config.name} Rent Scraper - {mode} mode[/]")
    console.print(f"   City: {city_config.name}, {city_config.country}")
    console.print(f"   Target: {city_config.work_address}")
    console.print(f"   Price range: {city_config.currency} {min_price} - {max_price}")
    console.print(f"   Output: {output_dir}")
    if site_filter:
        console.print(f"   Sites: {', '.join(site_filter)}")
    if max_listings:
        console.print(f"   Max listings per site: {max_listings}")
    if resume:
        console.print(f"   [green]Resume mode: enabled[/]")
    if stealth:
        # Check which stealth sites are available for this city
        available_stealth = [s for s, cfg in STEALTH_SITES.items() if cfg["city"] == city.lower()]
        if available_stealth:
            console.print(f"   [magenta]Stealth mode: enabled (available: {', '.join(available_stealth)})[/]")
        else:
            console.print(f"   [yellow]Stealth mode: no stealth scrapers available for {city}[/]")

    if apartments_only:
        console.print("   Filter: apartments only (no rooms/shared)")
    if min_surface:
        console.print(f"   Min surface: {min_surface} m²")
    if min_rooms:
        console.print(f"   Min rooms: {min_rooms}")

    run_pipeline(
        city=city,
        test_mode=test_run,
        site_filter=site_filter,
        skip_llm=skip_llm,
        output_dir=output_dir,
        min_price=min_price,
        max_price=max_price,
        max_listings_per_site=max_listings,
        apartments_only=apartments_only,
        min_surface=min_surface,
        min_rooms=min_rooms,
        resume=resume,
        stealth=stealth,
    )


@app.command()
def export(
    city: str = typer.Option(
        DEFAULT_CITY, "--city", "-c",
        help=f"City for export settings ({', '.join(CITIES.keys())})"
    ),
    format: ExportFormat = typer.Option(
        ExportFormat.both, "--format", "-f", help="Export format: excel, html, or both"
    ),
    output_dir: Path = typer.Option(
        Path("output"), "--output-dir", "-o", help="Output directory"
    ),
    db_path: Optional[Path] = typer.Option(
        None, "--db", "-d", help="Database path (default: output/{city}_listings.db)"
    ),
    min_price: Optional[int] = typer.Option(None, "--min-price", help="Minimum rent filter"),
    max_price: Optional[int] = typer.Option(None, "--max-price", help="Maximum rent filter"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filter by source site"),
    min_surface: Optional[int] = typer.Option(None, "--min-surface", help="Minimum surface area"),
    min_rooms: Optional[int] = typer.Option(None, "--min-rooms", help="Minimum number of rooms"),
    min_score: Optional[float] = typer.Option(
        None, "--min-score", help="Minimum neighborhood score"
    ),
):
    """
    Export listings from database to Excel/HTML without re-scraping.

    Examples:
        rent-scraper export --city amsterdam --format excel
        rent-scraper export --city helsinki --format html --min-price 1000
        rent-scraper export --source pararius --min-surface 60
    """
    from datetime import datetime

    from amsterdam_rent_scraper.export.excel import export_to_excel
    from amsterdam_rent_scraper.export.html_report import export_to_html
    from amsterdam_rent_scraper.storage.database import ListingDatabase

    # Get city configuration
    try:
        city_config = get_city_config(city)
    except ValueError as e:
        console.print(f"[red]{e}[/]")
        raise typer.Exit(1)

    city_lower = city.lower()

    # Determine database path (city-specific)
    if db_path is None:
        db_path = output_dir / f"{city_lower}_listings.db"
        # Fall back to legacy path for backward compatibility
        if not db_path.exists() and city_lower == "amsterdam":
            legacy_path = output_dir / "listings.db"
            if legacy_path.exists():
                db_path = legacy_path

    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/]")
        console.print(f"Run 'rent-scraper scrape --city {city}' first to create the database.")
        raise typer.Exit(1)

    console.print(f"[bold]Exporting from database: {db_path}[/]")
    console.print(f"   City: {city_config.name}")

    # Open database and get listings
    with ListingDatabase(db_path) as db:
        listings = db.get_all_listings(
            min_price=min_price,
            max_price=max_price,
            source_site=source,
            min_surface=min_surface,
            min_rooms=min_rooms,
            min_neighborhood_score=min_score,
        )

        if not listings:
            console.print("[yellow]No listings found matching filters.[/]")
            raise typer.Exit(0)

        # Show summary
        sources = db.get_sources_summary()
        console.print(f"\n[cyan]Database contains {db.get_listing_count()} total listings[/]")
        for site, count in sources.items():
            console.print(f"  {site}: {count}")

    console.print(f"\n[green]Exporting {len(listings)} listings matching filters...[/]")

    # Export
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format in (ExportFormat.excel, ExportFormat.both):
        excel_path = export_to_excel(
            listings, output_dir, f"{city_lower}_rentals_{timestamp}.xlsx"
        )
        export_to_excel(listings, output_dir, f"{city_lower}_rentals.xlsx")
        console.print(f"  Excel: {excel_path}")

    if format in (ExportFormat.html, ExportFormat.both):
        html_path = export_to_html(
            listings, output_dir, f"{city_lower}_rentals_{timestamp}.html",
            city=city,
        )
        export_to_html(listings, output_dir, f"{city_lower}_rentals.html", city=city)
        console.print(f"  HTML: {html_path}")

    console.print("\n[bold green]Export complete![/]")


@app.command()
def db_info(
    city: str = typer.Option(
        DEFAULT_CITY, "--city", "-c",
        help=f"City to show info for ({', '.join(CITIES.keys())})"
    ),
    db_path: Optional[Path] = typer.Option(
        None, "--db", "-d", help="Database path (default: output/{city}_listings.db)"
    ),
    output_dir: Path = typer.Option(
        Path("output"), "--output-dir", "-o", help="Output directory"
    ),
):
    """
    Show database statistics and summary.

    Examples:
        rent-scraper db-info
        rent-scraper db-info --city helsinki
        rent-scraper db-info --db /path/to/listings.db
    """
    from amsterdam_rent_scraper.storage.database import ListingDatabase

    city_lower = city.lower()

    if db_path is None:
        db_path = output_dir / f"{city_lower}_listings.db"
        # Fall back to legacy path for backward compatibility
        if not db_path.exists() and city_lower == "amsterdam":
            legacy_path = output_dir / "listings.db"
            if legacy_path.exists():
                db_path = legacy_path

    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/]")
        raise typer.Exit(1)

    with ListingDatabase(db_path) as db:
        total = db.get_listing_count()
        sources = db.get_sources_summary()

        console.print(f"\n[bold]Database: {db_path}[/]")
        console.print(f"[cyan]City: {city.capitalize()}[/]")
        console.print(f"[cyan]Total listings: {total}[/]\n")

        if sources:
            console.print("[bold]Listings by source:[/]")
            for site, count in sources.items():
                console.print(f"  {site}: {count}")
        else:
            console.print("[yellow]No listings in database.[/]")


@app.command()
def checkpoint(
    output_dir: Path = typer.Option(
        Path("output"), "--output-dir", "-o", help="Output directory"
    ),
    clear: bool = typer.Option(
        False, "--clear", "-c", help="Clear existing checkpoint"
    ),
):
    """
    Check or manage pipeline checkpoint status.

    Examples:
        rent-scraper checkpoint           # Show checkpoint status
        rent-scraper checkpoint --clear   # Clear checkpoint and start fresh
    """
    from amsterdam_rent_scraper.pipeline import load_checkpoint, clear_checkpoint, get_checkpoint_path

    checkpoint_path = get_checkpoint_path(output_dir)

    if clear:
        if checkpoint_path.exists():
            clear_checkpoint(output_dir)
            console.print("[green]Checkpoint cleared.[/]")
        else:
            console.print("[yellow]No checkpoint to clear.[/]")
        return

    checkpoint = load_checkpoint(output_dir)
    if checkpoint:
        console.print(f"\n[bold]Checkpoint found: {checkpoint_path}[/]")
        console.print(f"  Stage: [cyan]{checkpoint.get('stage')}[/]")
        console.print(f"  Listings: [cyan]{len(checkpoint.get('listings', []))}[/]")
        if checkpoint.get('stage') == 'geocoding':
            console.print(f"  Geocoding progress: [cyan]{checkpoint.get('geocoding_index', 0)}/{len(checkpoint.get('listings', []))}[/]")
        console.print(f"  Saved at: [dim]{checkpoint.get('saved_at')}[/]")
        console.print(f"\n[green]Run 'rent-scraper scrape --resume' to continue[/]")
    else:
        console.print("[yellow]No checkpoint found.[/]")


if __name__ == "__main__":
    app()
