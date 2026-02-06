"""CLI entry point for the Amsterdam rent scraper."""

from pathlib import Path

import typer
from rich.console import Console

app = typer.Typer(
    name="rent-scraper", help="Amsterdam rental listing scraper + LLM extraction"
)
console = Console()


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

    run_pipeline(
        test_mode=test_run,
        site_filter=site_filter,
        skip_llm=skip_llm,
        output_dir=output_dir,
        min_price=min_price,
        max_price=max_price,
        max_listings_per_site=max_listings,
    )


if __name__ == "__main__":
    app()
