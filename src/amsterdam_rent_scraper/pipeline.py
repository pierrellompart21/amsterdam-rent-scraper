"""Main pipeline that orchestrates scraping, LLM extraction, and export."""

import importlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from amsterdam_rent_scraper.config.settings import (
    AMSTERDAM_AREA_LOCATIONS,
    STOCKHOLM_AREA_LOCATIONS,
    DEFAULT_CITY,
    OUTPUT_DIR,
    STEALTH_SITES,
    get_city_config,
    get_enabled_sites,
)
from amsterdam_rent_scraper.export.excel import export_to_excel
from amsterdam_rent_scraper.export.html_report import export_to_html
from amsterdam_rent_scraper.export.failed_listings import export_failed_listings
from amsterdam_rent_scraper.utils.notifications import send_pipeline_notification
from amsterdam_rent_scraper.llm.extractor import OllamaExtractor
from amsterdam_rent_scraper.llm.regex_fallback import regex_extract_from_html
from amsterdam_rent_scraper.models.listing import RentalListing
from amsterdam_rent_scraper.storage.database import ListingDatabase
from amsterdam_rent_scraper.utils.geo import enrich_listing_with_geo, GeoEnrichmentResult

console = Console()

# Checkpoint stages
STAGE_SCRAPING = "scraping"
STAGE_LLM_EXTRACTION = "llm_extraction"
STAGE_FILTERING = "filtering"
STAGE_GEOCODING = "geocoding"
STAGE_COMPLETE = "complete"


@dataclass
class StageStats:
    """Statistics for a single pipeline stage."""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    fallback: int = 0  # Used fallback method

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total == 0:
            return 0.0
        return (self.success / self.total) * 100


@dataclass
class PipelineStats:
    """Track statistics across all pipeline stages."""
    scraping: dict[str, StageStats] = field(default_factory=dict)  # Per-site stats
    llm_extraction: StageStats = field(default_factory=StageStats)
    geocoding: StageStats = field(default_factory=StageStats)
    routing: StageStats = field(default_factory=StageStats)
    database: StageStats = field(default_factory=StageStats)
    filtering: dict[str, int] = field(default_factory=dict)  # Reason -> count
    data_quality: dict[str, int] = field(default_factory=dict)  # Missing field -> count
    failed_geocoding_indices: list[int] = field(default_factory=list)  # Indices of listings that failed geocoding
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate pipeline duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def total_failures(self) -> int:
        """Total number of failures across all stages."""
        return (
            self.llm_extraction.failed +
            self.geocoding.failed +
            self.routing.failed +
            self.database.failed
        )

    def calculate_data_quality(self, listings: list[dict]) -> None:
        """Calculate data quality statistics for listings."""
        critical_fields = ["price_eur", "address", "surface_m2", "rooms"]

        for field in critical_fields:
            missing = sum(1 for l in listings if not l.get(field))
            if missing > 0:
                self.data_quality[f"Missing {field}"] = missing

        # Check for listings with coordinates
        no_coords = sum(1 for l in listings if not l.get("latitude") or not l.get("longitude"))
        if no_coords > 0:
            self.data_quality["Missing coordinates"] = no_coords

    def print_summary(self) -> None:
        """Print a formatted summary of all statistics."""
        console.print("\n[bold cyan]═══ Pipeline Statistics ═══[/]")

        # Scraping stats
        if self.scraping:
            table = Table(title="Scraping by Site", show_header=True)
            table.add_column("Site", style="cyan")
            table.add_column("Total", justify="right")
            table.add_column("Success", justify="right", style="green")
            table.add_column("Failed", justify="right", style="red")
            table.add_column("Rate", justify="right")

            total_scraped = 0
            total_success = 0
            total_failed = 0
            for site, stats in sorted(self.scraping.items()):
                rate = f"{stats.success_rate:.1f}%"
                table.add_row(site, str(stats.total), str(stats.success), str(stats.failed), rate)
                total_scraped += stats.total
                total_success += stats.success
                total_failed += stats.failed

            if len(self.scraping) > 1:
                total_rate = (total_success / total_scraped * 100) if total_scraped > 0 else 0
                table.add_row("─" * 10, "─" * 5, "─" * 5, "─" * 5, "─" * 5)
                table.add_row("[bold]TOTAL[/]", str(total_scraped), str(total_success), str(total_failed), f"{total_rate:.1f}%")

            console.print(table)

        # LLM Extraction stats
        if self.llm_extraction.total > 0:
            self._print_stage_stats("LLM Extraction", self.llm_extraction)

        # Geocoding stats
        if self.geocoding.total > 0:
            self._print_stage_stats("Geocoding", self.geocoding)

        # Routing stats
        if self.routing.total > 0:
            self._print_stage_stats("Routing (Bike/Transit)", self.routing)

        # Filtering stats
        if self.filtering:
            console.print("\n[bold]Filtering:[/]")
            for reason, count in self.filtering.items():
                console.print(f"  {reason}: [yellow]{count}[/]")

        # Database stats
        if self.database.total > 0:
            self._print_stage_stats("Database", self.database)

        # Data quality stats
        if self.data_quality:
            console.print("\n[bold]Data Quality (missing fields):[/]")
            for field, count in sorted(self.data_quality.items()):
                console.print(f"  {field}: [yellow]{count}[/]")

    def get_text_summary(self) -> str:
        """Get a plain text summary of stats for email notifications."""
        lines = []

        # Scraping
        if self.scraping:
            lines.append("SCRAPING:")
            for site, stats in sorted(self.scraping.items()):
                lines.append(f"  {site}: {stats.success}/{stats.total} ({stats.success_rate:.1f}%)")

        # LLM Extraction
        if self.llm_extraction.total > 0:
            lines.append(f"\nLLM EXTRACTION:")
            lines.append(f"  Success: {self.llm_extraction.success}/{self.llm_extraction.total} ({self.llm_extraction.success_rate:.1f}%)")
            if self.llm_extraction.failed > 0:
                lines.append(f"  Failed: {self.llm_extraction.failed}")

        # Geocoding
        if self.geocoding.total > 0:
            lines.append(f"\nGEOCODING:")
            lines.append(f"  Success: {self.geocoding.success}/{self.geocoding.total} ({self.geocoding.success_rate:.1f}%)")
            if self.geocoding.fallback > 0:
                lines.append(f"  Fallback (city center): {self.geocoding.fallback}")
            if self.geocoding.failed > 0:
                lines.append(f"  Failed: {self.geocoding.failed}")

        # Routing
        if self.routing.total > 0:
            lines.append(f"\nROUTING:")
            lines.append(f"  Success: {self.routing.success}/{self.routing.total} ({self.routing.success_rate:.1f}%)")

        # Filtering
        if self.filtering:
            lines.append(f"\nFILTERING:")
            for reason, count in self.filtering.items():
                lines.append(f"  {reason}: {count}")

        # Database
        if self.database.total > 0:
            lines.append(f"\nDATABASE:")
            lines.append(f"  Success: {self.database.success}/{self.database.total}")
            if self.database.failed > 0:
                lines.append(f"  Failed: {self.database.failed}")

        # Data quality
        if self.data_quality:
            lines.append(f"\nDATA QUALITY:")
            for field, count in sorted(self.data_quality.items()):
                lines.append(f"  {field}: {count}")

        return "\n".join(lines)

    def _print_stage_stats(self, name: str, stats: StageStats) -> None:
        """Print stats for a single stage."""
        console.print(f"\n[bold]{name}:[/]")
        console.print(f"  Total: {stats.total}")
        console.print(f"  [green]Success: {stats.success}[/] ({stats.success_rate:.1f}%)")
        if stats.fallback > 0:
            console.print(f"  [yellow]Fallback: {stats.fallback}[/] (used city center)")
        if stats.failed > 0:
            console.print(f"  [red]Failed: {stats.failed}[/]")
        if stats.skipped > 0:
            console.print(f"  [dim]Skipped: {stats.skipped}[/]")


def create_progress(description: str = "") -> Progress:
    """Create a rich progress bar."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[cyan]{task.description}"),
        BarColumn(bar_width=30),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


def load_scraper_class(dotted_path: str):
    """Dynamically load a scraper class from its dotted path."""
    module_path, class_name = dotted_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def get_checkpoint_path(output_dir: Path) -> Path:
    """Get the path to the checkpoint file."""
    return output_dir / ".pipeline_checkpoint.json"


def save_checkpoint(
    output_dir: Path,
    stage: str,
    listings: list[dict],
    geocoding_index: int = 0,
    config: dict = None,
):
    """Save pipeline checkpoint to disk."""
    checkpoint_path = get_checkpoint_path(output_dir)

    # Convert datetime objects to ISO format strings for JSON serialization
    serializable_listings = []
    for listing in listings:
        listing_copy = listing.copy()
        for key, value in listing_copy.items():
            if isinstance(value, datetime):
                listing_copy[key] = value.isoformat()
        serializable_listings.append(listing_copy)

    checkpoint = {
        "stage": stage,
        "geocoding_index": geocoding_index,
        "listings": serializable_listings,
        "config": config or {},
        "saved_at": datetime.now().isoformat(),
    }

    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    console.print(f"[dim]Checkpoint saved: {stage} ({len(listings)} listings)[/]")


def load_checkpoint(output_dir: Path) -> Optional[dict]:
    """Load pipeline checkpoint from disk."""
    checkpoint_path = get_checkpoint_path(output_dir)

    if not checkpoint_path.exists():
        return None

    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            checkpoint = json.load(f)

        # Convert ISO format strings back to datetime objects
        for listing in checkpoint.get("listings", []):
            for key, value in listing.items():
                if key == "scraped_at" and isinstance(value, str):
                    try:
                        listing[key] = datetime.fromisoformat(value)
                    except ValueError:
                        pass

        return checkpoint
    except (json.JSONDecodeError, KeyError) as e:
        console.print(f"[yellow]Warning: Could not load checkpoint: {e}[/]")
        return None


def clear_checkpoint(output_dir: Path):
    """Remove the checkpoint file."""
    checkpoint_path = get_checkpoint_path(output_dir)
    if checkpoint_path.exists():
        checkpoint_path.unlink()


def run_pipeline(
    city: str = None,
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
    resume: bool = False,
    stealth: bool = False,
) -> list[dict]:
    """
    Run the full scraping pipeline.

    1. Get enabled sites (filtered if specified)
    2. For each site, run the scraper
    3. Optionally enrich with LLM extraction
    4. Add geographic data
    5. Export to Excel and HTML

    If resume=True, attempts to continue from the last checkpoint.
    """
    # Initialize pipeline statistics
    stats = PipelineStats()
    stats.start_time = datetime.now()

    # Get city configuration
    city = city or DEFAULT_CITY
    city_config = get_city_config(city)
    city_lower = city.lower()

    output_dir = Path(output_dir or OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use city defaults if not specified
    min_price = min_price if min_price is not None else city_config.min_price
    max_price = max_price if max_price is not None else city_config.max_price

    # Store config for checkpoint
    config = {
        "city": city,
        "test_mode": test_mode,
        "site_filter": site_filter,
        "skip_llm": skip_llm,
        "min_price": min_price,
        "max_price": max_price,
        "max_listings_per_site": max_listings_per_site,
        "apartments_only": apartments_only,
        "min_surface": min_surface,
        "min_rooms": min_rooms,
        "stealth": stealth,
    }

    # Check for existing checkpoint
    checkpoint = None
    start_stage = STAGE_SCRAPING
    all_listings = []
    geocoding_start_index = 0

    if resume:
        checkpoint = load_checkpoint(output_dir)
        if checkpoint:
            start_stage = checkpoint.get("stage", STAGE_SCRAPING)
            all_listings = checkpoint.get("listings", [])
            geocoding_start_index = checkpoint.get("geocoding_index", 0)

            console.print(f"\n[bold green]Resuming from checkpoint[/]")
            console.print(f"  Stage: {start_stage}")
            console.print(f"  Listings: {len(all_listings)}")
            if start_stage == STAGE_GEOCODING:
                console.print(f"  Geocoding progress: {geocoding_start_index}/{len(all_listings)}")
        else:
            console.print("[yellow]No checkpoint found, starting fresh[/]")

    sites = get_enabled_sites(site_filter, city=city)

    # Build list of stealth sites to scrape (if stealth mode enabled)
    stealth_sites_to_scrape = []
    if stealth and site_filter:
        # Check which requested sites have stealth scrapers
        for site_name in site_filter:
            site_lower = site_name.lower()
            if site_lower in STEALTH_SITES:
                stealth_cfg = STEALTH_SITES[site_lower]
                if stealth_cfg["city"] == city_lower:
                    stealth_sites_to_scrape.append((site_lower, stealth_cfg))

    if not sites and not stealth_sites_to_scrape and start_stage == STAGE_SCRAPING:
        console.print("[red]No sites to scrape. Check your --sites filter.[/]")
        return []

    if start_stage == STAGE_SCRAPING:
        console.print(f"\n[bold]Starting scrape pipeline[/]")
        if max_listings_per_site:
            console.print(f"  Mode: CUSTOM ({max_listings_per_site} listings/site)")
        else:
            console.print(f"  Mode: {'TEST (3 listings/site)' if test_mode else 'FULL'}")

        # Show which sites we're scraping
        regular_site_names = [s.name for s in sites]
        stealth_site_names = [s[0] for s in stealth_sites_to_scrape]
        if regular_site_names:
            console.print(f"  Sites: {', '.join(regular_site_names)}")
        if stealth_site_names:
            console.print(f"  [magenta]Stealth sites: {', '.join(stealth_site_names)}[/]")
        console.print(f"  Price range: EUR {min_price} - {max_price}")
        console.print("")

        all_listings = []

        # Get locations for this city (Amsterdam and Stockholm areas have multiple cities, others have just one)
        if city_lower == "amsterdam":
            locations = AMSTERDAM_AREA_LOCATIONS
        elif city_lower == "stockholm":
            locations = STOCKHOLM_AREA_LOCATIONS
        else:
            locations = [city_lower]
        console.print(f"  Locations to search: {', '.join(locations)}")
        console.print("")

        # Run regular scrapers
        for site in sites:
            console.print(f"\n[bold cyan]>>> {site.name.upper()}[/]")
            site_stats = StageStats()

            for location in locations:
                console.print(f"  [dim]Location: {location}[/]")
                try:
                    scraper_class = load_scraper_class(site.scraper_class)
                    scraper = scraper_class(
                        min_price=min_price,
                        max_price=max_price,
                        test_mode=test_mode,
                        max_listings=max_listings_per_site,
                        location=location,
                    )
                    listings = scraper.scrape_all()
                    all_listings.extend(listings)
                    site_stats.total += len(listings)
                    site_stats.success += len(listings)
                except ImportError as e:
                    console.print(f"[yellow]Scraper not implemented yet: {site.name} ({e})[/]")
                    site_stats.failed += 1
                    break  # No point trying other locations if scraper doesn't exist
                except Exception as e:
                    console.print(f"[red]Error scraping {site.name} for {location}: {e}[/]")
                    site_stats.failed += 1

            stats.scraping[site.name] = site_stats

        # Run stealth scrapers (if stealth mode is enabled)
        for site_name, stealth_cfg in stealth_sites_to_scrape:
            console.print(f"\n[bold magenta]>>> {site_name.upper()} (STEALTH)[/]")
            site_stats = StageStats()

            for location in locations:
                console.print(f"  [dim]Location: {location}[/]")
                try:
                    scraper_class = load_scraper_class(stealth_cfg["stealth_class"])
                    scraper = scraper_class(
                        min_price=min_price,
                        max_price=max_price,
                        test_mode=test_mode,
                        max_listings=max_listings_per_site,
                        location=location,
                    )
                    listings = scraper.scrape_all()
                    all_listings.extend(listings)
                    site_stats.total += len(listings)
                    site_stats.success += len(listings)
                except ImportError as e:
                    console.print(
                        f"[yellow]Stealth scraper unavailable: {site_name}. "
                        f"Install with: pip install undetected-chromedriver ({e})[/]"
                    )
                    site_stats.failed += 1
                    break  # No point trying other locations
                except Exception as e:
                    console.print(f"[red]Error in stealth scraper {site_name} for {location}: {e}[/]")
                    site_stats.failed += 1

            stats.scraping[f"{site_name} (stealth)"] = site_stats

        if not all_listings:
            console.print("[yellow]No listings scraped.[/]")
            return []

        console.print(f"\n[bold]Total raw listings: {len(all_listings)}[/]")

        # Deduplicate listings by URL (same listing may appear in multiple location searches)
        seen_urls = set()
        unique_listings = []
        for listing in all_listings:
            url = listing.get("listing_url") or listing.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_listings.append(listing)
            elif not url:
                # Keep listings without URLs (shouldn't happen, but be safe)
                unique_listings.append(listing)

        duplicates_removed = len(all_listings) - len(unique_listings)
        if duplicates_removed > 0:
            console.print(f"[dim]Removed {duplicates_removed} duplicate listings[/]")
        all_listings = unique_listings

        console.print(f"[bold]Unique listings: {len(all_listings)}[/]")

        # Save checkpoint after scraping
        save_checkpoint(output_dir, STAGE_LLM_EXTRACTION, all_listings, config=config)
        start_stage = STAGE_LLM_EXTRACTION

    # LLM enrichment (or regex fallback)
    if start_stage == STAGE_LLM_EXTRACTION:
        stats.llm_extraction.total = len(all_listings)

        if not skip_llm:
            console.print("\n[bold cyan]Running LLM extraction...[/]")
            extractor = OllamaExtractor()

            if extractor.is_available():
                with create_progress() as progress:
                    task = progress.add_task("LLM extraction", total=len(all_listings))
                    for listing in all_listings:
                        raw_path = listing.get("raw_page_path")
                        if raw_path:
                            enriched, success = extractor.enrich_listing(listing, raw_path)
                            listing.update(enriched)
                            if success:
                                stats.llm_extraction.success += 1
                            else:
                                stats.llm_extraction.failed += 1
                        else:
                            stats.llm_extraction.skipped += 1
                        progress.advance(task)
            else:
                console.print(
                    "[yellow]Skipping LLM extraction (Ollama not available)[/]"
                )
                stats.llm_extraction.skipped = len(all_listings)
                # Use regex fallback instead
                console.print("[cyan]Using regex fallback extraction...[/]")
                with create_progress() as progress:
                    task = progress.add_task("Regex extraction", total=len(all_listings))
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
            console.print("[dim]Skipping LLM extraction (--skip-llm)[/]")
            stats.llm_extraction.skipped = len(all_listings)
            # Still apply regex fallback for basic field extraction
            console.print("[cyan]Using regex fallback extraction...[/]")
            with create_progress() as progress:
                task = progress.add_task("Regex extraction", total=len(all_listings))
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

        # Save checkpoint after LLM extraction
        save_checkpoint(output_dir, STAGE_FILTERING, all_listings, config=config)
        start_stage = STAGE_FILTERING

    # Filtering stage
    if start_stage == STAGE_FILTERING:
        console.print("\n[bold cyan]Applying filters...[/]")

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
            stats.filtering[f"Price outside EUR {min_price}-{max_price}"] = price_filtered
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
                stats.filtering["Room/shared listings"] = rooms_filtered
                console.print(f"[yellow]Filtered {rooms_filtered} room/shared listings (apartments only mode)[/]")

        # Filter by minimum surface area
        if min_surface:
            pre_filter_count = len(all_listings)
            all_listings = [
                listing for listing in all_listings
                if listing.get("surface_m2") is None  # Keep if no surface data
                or listing.get("surface_m2", 0) >= min_surface
            ]
            surface_filtered = pre_filter_count - len(all_listings)
            if surface_filtered > 0:
                stats.filtering[f"Below {min_surface} m²"] = surface_filtered
                console.print(f"[yellow]Filtered {surface_filtered} listings below {min_surface} m²[/]")

        # Filter by minimum rooms
        if min_rooms:
            pre_filter_count = len(all_listings)
            all_listings = [
                listing for listing in all_listings
                if listing.get("rooms") is None  # Keep if no room data
                or listing.get("rooms", 0) >= min_rooms
            ]
            rooms_filtered = pre_filter_count - len(all_listings)
            if rooms_filtered > 0:
                stats.filtering[f"Fewer than {min_rooms} rooms"] = rooms_filtered
                console.print(f"[yellow]Filtered {rooms_filtered} listings with fewer than {min_rooms} rooms[/]")

        # Save checkpoint before geocoding
        save_checkpoint(output_dir, STAGE_GEOCODING, all_listings, geocoding_index=0, config=config)
        start_stage = STAGE_GEOCODING
        geocoding_start_index = 0

    # Geographic enrichment
    if start_stage == STAGE_GEOCODING:
        console.print("\n[bold cyan]Adding geographic data...[/]")

        # Save checkpoint every N listings during geocoding
        GEOCODING_CHECKPOINT_INTERVAL = 50

        stats.geocoding.total = len(all_listings)
        stats.routing.total = len(all_listings)

        with create_progress() as progress:
            task = progress.add_task("Geocoding", total=len(all_listings))

            # Skip already processed listings if resuming
            if geocoding_start_index > 0:
                progress.update(task, completed=geocoding_start_index)
                # Estimate already processed stats (can't know exact values on resume)
                stats.geocoding.success = geocoding_start_index

            for i, listing in enumerate(all_listings):
                if i < geocoding_start_index:
                    continue  # Skip already processed

                _, geo_result = enrich_listing_with_geo(listing, city=city)

                # Track geocoding success/failure
                if geo_result.geocode_success:
                    stats.geocoding.success += 1
                    if geo_result.geocode_used_fallback:
                        stats.geocoding.fallback += 1
                        # Track for potential retry (fallback means original geocoding failed)
                        stats.failed_geocoding_indices.append(i)
                else:
                    stats.geocoding.failed += 1
                    stats.failed_geocoding_indices.append(i)

                # Track routing success
                if geo_result.bike_route_success or geo_result.transit_route_success:
                    stats.routing.success += 1
                elif geo_result.geocode_success:  # Only count as failed if we had coords
                    stats.routing.failed += 1

                progress.advance(task)

                # Save checkpoint periodically
                if (i + 1) % GEOCODING_CHECKPOINT_INTERVAL == 0:
                    save_checkpoint(
                        output_dir, STAGE_GEOCODING, all_listings,
                        geocoding_index=i + 1, config=config
                    )

        # Retry queue for failed geocoding (wait and try again)
        if stats.failed_geocoding_indices:
            retry_count = len(stats.failed_geocoding_indices)
            console.print(f"\n[bold yellow]Retrying {retry_count} failed geocoding attempts...[/]")
            console.print("[dim]Waiting 60 seconds before retry (rate limit cooldown)...[/]")
            import time
            time.sleep(60)  # Wait for rate limit to reset

            retried = 0
            succeeded = 0
            with create_progress() as progress:
                task = progress.add_task("Geocoding retry", total=retry_count)

                for idx in stats.failed_geocoding_indices:
                    listing = all_listings[idx]

                    # Skip if already has real coordinates (not fallback)
                    # Check if coordinates match a city center (fallback)
                    from amsterdam_rent_scraper.config.settings import get_location_center
                    current_coords = (listing.get("latitude"), listing.get("longitude"))
                    listing_city = listing.get("city", city)
                    fallback_coords = get_location_center(listing_city) or get_location_center(city)

                    # Only retry if using fallback or no coords
                    if current_coords == fallback_coords or not current_coords[0]:
                        _, geo_result = enrich_listing_with_geo(listing, city=city)
                        retried += 1
                        if geo_result.geocode_success and not geo_result.geocode_used_fallback:
                            succeeded += 1
                            stats.geocoding.fallback -= 1  # No longer using fallback

                    progress.advance(task)

            console.print(f"[green]Retry complete: {succeeded}/{retried} succeeded[/]")

    # Add scraped timestamp
    now = datetime.now()
    for listing in all_listings:
        if "scraped_at" not in listing:
            listing["scraped_at"] = now

    # Save to database (city-specific)
    console.print("\n[bold cyan]Saving to database...[/]")
    db_path = output_dir / f"{city_lower}_listings.db"
    with ListingDatabase(db_path) as db:
        new_count, updated_count, error_count = db.bulk_upsert(all_listings)
        total_in_db = db.get_listing_count()

        stats.database.total = len(all_listings)
        stats.database.success = new_count + updated_count
        stats.database.failed = error_count

        console.print(f"  [green]New: {new_count}[/], [yellow]Updated: {updated_count}[/], [red]Errors: {error_count}[/], Total in DB: {total_in_db}")

    # Export (city-specific filenames)
    console.print("\n[bold cyan]Exporting results...[/]")
    timestamp = now.strftime("%Y%m%d_%H%M%S")

    excel_path = export_to_excel(
        all_listings, output_dir, f"{city_lower}_rentals_{timestamp}.xlsx"
    )
    html_path = export_to_html(
        all_listings, output_dir, f"{city_lower}_rentals_{timestamp}.html", city=city
    )

    # Also export latest versions without timestamp
    export_to_excel(all_listings, output_dir, f"{city_lower}_rentals.xlsx")
    export_to_html(all_listings, output_dir, f"{city_lower}_rentals.html", city=city)

    # Clear checkpoint on successful completion
    clear_checkpoint(output_dir)

    # Calculate data quality stats
    stats.calculate_data_quality(all_listings)

    # Export failed listings for review
    failed_path = export_failed_listings(all_listings, output_dir, city)

    # Record end time
    stats.end_time = datetime.now()

    # Print statistics summary
    stats.print_summary()

    console.print("\n[bold green]Pipeline complete![/]")
    console.print(f"  Listings: {len(all_listings)}")
    console.print(f"  Database: {db_path}")
    console.print(f"  Excel: {excel_path}")
    console.print(f"  HTML: {html_path}")
    if failed_path:
        console.print(f"  [yellow]Failed listings: {failed_path}[/]")

    # Send email notification
    send_pipeline_notification(
        stats_summary=stats.get_text_summary(),
        listings_count=len(all_listings),
        city=city,
        excel_path=str(excel_path),
        html_path=str(html_path),
        failed_count=stats.total_failures,
        duration_seconds=stats.duration_seconds,
    )

    return all_listings
