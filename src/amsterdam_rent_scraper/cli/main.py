"""CLI entry point for the Amsterdam rent scraper."""

from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="rent-scraper", help="Amsterdam rental listing scraper + LLM extraction"
)
console = Console()


class ExportFormat(str, Enum):
    """Export format options."""
    excel = "excel"
    html = "html"
    both = "both"


@app.command()
def scrape(
    test_run: bool = typer.Option(
        False, "--test-run", "-t", help="Scrape only 3 listings per site"
    ),
    full_run: bool = typer.Option(
        False, "--full-run", "-f", help="Scrape all listings from all sites"
    ),
    sites: list[str] = typer.Option(
        None, "--sites", "-s", help="Filter specific sites (e.g. funda,pararius)"
    ),
    max_listings: int = typer.Option(
        None, "--max-listings", "-n", help="Max listings per site (overrides --test-run limit)"
    ),
    min_price: int = typer.Option(1000, "--min-price", help="Minimum rent in EUR"),
    max_price: int = typer.Option(2000, "--max-price", help="Maximum rent in EUR"),
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
        None, "--min-surface", help="Minimum surface area in m²"
    ),
    min_rooms: int = typer.Option(
        None, "--min-rooms", help="Minimum number of rooms"
    ),
    ollama_model: str = typer.Option(
        "llama3", "--model", "-m", help="Ollama model name"
    ),
):
    """
    Scrape Dutch rental websites for Amsterdam/Amstelveen apartments.

    Examples:
        rent-scraper --test-run
        rent-scraper --full-run --sites funda,pararius
        rent-scraper -t --min-price 1200 --max-price 1800
    """
    from amsterdam_rent_scraper.pipeline import run_pipeline

    site_filter = None
    if sites:
        # Handle both --sites funda --sites pararius AND --sites funda,pararius
        site_filter = []
        for s in sites:
            site_filter.extend(s.split(","))

    mode = "test" if test_run else "full"
    console.print(f"[bold]Amsterdam Rent Scraper - {mode} mode[/]")
    console.print(f"   Price range: EUR {min_price} - {max_price}")
    console.print(f"   Output: {output_dir}")
    if site_filter:
        console.print(f"   Sites: {', '.join(site_filter)}")
    if max_listings:
        console.print(f"   Max listings per site: {max_listings}")

    if apartments_only:
        console.print("   Filter: apartments only (no rooms/shared)")
    if min_surface:
        console.print(f"   Min surface: {min_surface} m²")
    if min_rooms:
        console.print(f"   Min rooms: {min_rooms}")

    run_pipeline(
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
    )


@app.command()
def export(
    format: ExportFormat = typer.Option(
        ExportFormat.both, "--format", "-f", help="Export format: excel, html, or both"
    ),
    output_dir: Path = typer.Option(
        Path("output"), "--output-dir", "-o", help="Output directory"
    ),
    db_path: Optional[Path] = typer.Option(
        None, "--db", "-d", help="Database path (default: output/listings.db)"
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
        rent-scraper export --format excel
        rent-scraper export --format html --min-price 1200 --max-price 1800
        rent-scraper export --source pararius --min-surface 60
    """
    from datetime import datetime

    from amsterdam_rent_scraper.export.excel import export_to_excel
    from amsterdam_rent_scraper.export.html_report import export_to_html
    from amsterdam_rent_scraper.storage.database import ListingDatabase

    # Determine database path
    if db_path is None:
        db_path = output_dir / "listings.db"

    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/]")
        console.print("Run 'rent-scraper' first to scrape and create the database.")
        raise typer.Exit(1)

    console.print(f"[bold]Exporting from database: {db_path}[/]")

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
            listings, output_dir, f"amsterdam_rentals_{timestamp}.xlsx"
        )
        export_to_excel(listings, output_dir, "amsterdam_rentals.xlsx")
        console.print(f"  Excel: {excel_path}")

    if format in (ExportFormat.html, ExportFormat.both):
        html_path = export_to_html(
            listings, output_dir, f"amsterdam_rentals_{timestamp}.html"
        )
        export_to_html(listings, output_dir, "amsterdam_rentals.html")
        console.print(f"  HTML: {html_path}")

    console.print("\n[bold green]Export complete![/]")


@app.command()
def db_info(
    db_path: Optional[Path] = typer.Option(
        None, "--db", "-d", help="Database path (default: output/listings.db)"
    ),
    output_dir: Path = typer.Option(
        Path("output"), "--output-dir", "-o", help="Output directory"
    ),
):
    """
    Show database statistics and summary.

    Examples:
        rent-scraper db-info
        rent-scraper db-info --db /path/to/listings.db
    """
    from amsterdam_rent_scraper.storage.database import ListingDatabase

    if db_path is None:
        db_path = output_dir / "listings.db"

    if not db_path.exists():
        console.print(f"[red]Database not found: {db_path}[/]")
        raise typer.Exit(1)

    with ListingDatabase(db_path) as db:
        total = db.get_listing_count()
        sources = db.get_sources_summary()

        console.print(f"\n[bold]Database: {db_path}[/]")
        console.print(f"[cyan]Total listings: {total}[/]\n")

        if sources:
            console.print("[bold]Listings by source:[/]")
            for site, count in sources.items():
                console.print(f"  {site}: {count}")
        else:
            console.print("[yellow]No listings in database.[/]")


if __name__ == "__main__":
    app()
