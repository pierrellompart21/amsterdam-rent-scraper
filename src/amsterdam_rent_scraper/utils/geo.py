"""Geographic utilities for distance and commute calculations."""

import math
from typing import Optional, Tuple

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from rich.console import Console

from amsterdam_rent_scraper.config.settings import WORK_LAT, WORK_LNG

console = Console()

# Initialize geocoder
geolocator = Nominatim(user_agent="amsterdam_rent_scraper")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in km."""
    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """Geocode an address to latitude/longitude coordinates."""
    if not address:
        return None

    # Add Netherlands if not present
    if "netherlands" not in address.lower() and "nl" not in address.lower():
        address = f"{address}, Netherlands"

    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except GeocoderTimedOut:
        console.print(f"[yellow]Geocoding timed out for: {address}[/]")
    except Exception as e:
        console.print(f"[yellow]Geocoding failed for {address}: {e}[/]")

    return None


def calculate_distance_to_work(lat: float, lon: float) -> float:
    """Calculate distance from a point to the work location."""
    return haversine_distance(lat, lon, WORK_LAT, WORK_LNG)


def estimate_commute_times(distance_km: float) -> Tuple[int, int]:
    """
    Estimate commute times based on distance.

    Returns (bike_minutes, transit_minutes).
    These are rough estimates - actual times vary by route.
    """
    # Average cycling speed in NL: ~18 km/h
    bike_speed_kmh = 18
    bike_minutes = int((distance_km / bike_speed_kmh) * 60)

    # Transit is harder to estimate, assume average 25 km/h including waiting
    transit_speed_kmh = 25
    transit_minutes = int((distance_km / transit_speed_kmh) * 60) + 10  # +10 for walking/waiting

    return (bike_minutes, transit_minutes)


def enrich_listing_with_geo(listing: dict) -> dict:
    """Add geographic data to a listing."""
    # Try to get coordinates
    lat = listing.get("latitude")
    lon = listing.get("longitude")

    if not lat or not lon:
        # Try to geocode from address
        address = listing.get("address") or listing.get("title")
        if address:
            postal = listing.get("postal_code")
            if postal:
                address = f"{address}, {postal}"
            coords = geocode_address(address)
            if coords:
                listing["latitude"] = coords[0]
                listing["longitude"] = coords[1]
                lat, lon = coords

    # Calculate distance and commute times
    if lat and lon:
        distance = calculate_distance_to_work(lat, lon)
        listing["distance_km"] = round(distance, 2)

        bike_min, transit_min = estimate_commute_times(distance)
        listing["commute_time_bike_min"] = bike_min
        listing["commute_time_transit_min"] = transit_min

    return listing
