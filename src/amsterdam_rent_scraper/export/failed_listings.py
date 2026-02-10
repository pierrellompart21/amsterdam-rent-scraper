"""Export failed or problematic listings for review."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def export_failed_listings(
    listings: list[dict],
    output_dir: Path,
    city: str,
    failure_reasons: dict[str, list[dict]] = None,
) -> Optional[Path]:
    """Export listings with issues to a JSON file for review.

    Args:
        listings: All listings
        output_dir: Output directory
        city: City name for filename
        failure_reasons: Dict mapping reason to list of failed listing dicts

    Returns:
        Path to the exported file, or None if no failures
    """
    # Categorize problematic listings
    issues = {
        "missing_price": [],
        "missing_coordinates": [],
        "missing_address": [],
        "geocoding_fallback": [],  # Used city center
        "missing_surface": [],
        "missing_rooms": [],
    }

    for listing in listings:
        url = listing.get("listing_url", "unknown")
        title = listing.get("title", "No title")
        source = listing.get("source_site", "unknown")

        summary = {
            "url": url,
            "title": title,
            "source": source,
            "city": listing.get("city"),
            "address": listing.get("address"),
            "postal_code": listing.get("postal_code"),
        }

        if not listing.get("price_eur"):
            issues["missing_price"].append(summary)

        if not listing.get("latitude") or not listing.get("longitude"):
            issues["missing_coordinates"].append(summary)

        if not listing.get("address"):
            issues["missing_address"].append(summary)

        if not listing.get("surface_m2"):
            issues["missing_surface"].append(summary)

        if not listing.get("rooms"):
            issues["missing_rooms"].append(summary)

    # Add external failure reasons if provided
    if failure_reasons:
        for reason, failed_items in failure_reasons.items():
            if reason not in issues:
                issues[reason] = []
            issues[reason].extend(failed_items)

    # Remove empty categories
    issues = {k: v for k, v in issues.items() if v}

    if not issues:
        console.print("[dim]No failed listings to export[/]")
        return None

    # Build export structure
    export_data = {
        "generated_at": datetime.now().isoformat(),
        "city": city,
        "total_listings": len(listings),
        "summary": {reason: len(items) for reason, items in issues.items()},
        "issues": issues,
    }

    # Write to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{city.lower()}_failed_listings_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    console.print(f"[yellow]Failed listings exported: {output_path}[/]")

    # Print summary
    console.print("\n[bold]Issues Summary:[/]")
    for reason, items in sorted(issues.items()):
        console.print(f"  {reason}: [yellow]{len(items)}[/]")

    return output_path


def export_geocoding_failures(
    failed_addresses: list[dict],
    output_dir: Path,
    city: str,
) -> Optional[Path]:
    """Export addresses that failed geocoding for manual review/retry.

    Args:
        failed_addresses: List of dicts with address info that failed
        output_dir: Output directory
        city: City name

    Returns:
        Path to the exported file, or None if no failures
    """
    if not failed_addresses:
        return None

    export_data = {
        "generated_at": datetime.now().isoformat(),
        "city": city,
        "total_failed": len(failed_addresses),
        "addresses": failed_addresses,
    }

    output_path = output_dir / f"{city.lower()}_geocoding_failures.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)

    console.print(f"[yellow]Geocoding failures exported: {output_path}[/]")
    return output_path
