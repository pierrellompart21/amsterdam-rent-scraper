"""Geographic utilities for distance and commute calculations."""

import math
import time
from typing import Optional, Tuple

import httpx
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from rich.console import Console

from amsterdam_rent_scraper.config.settings import WORK_LAT, WORK_LNG

console = Console()

# Initialize geocoder
geolocator = Nominatim(user_agent="amsterdam_rent_scraper")

# OSRM public demo server (free, no API key required)
OSRM_BASE_URL = "http://router.project-osrm.org/route/v1"

# Rate limiting for OSRM (be respectful to free service)
_last_osrm_request = 0.0
OSRM_MIN_INTERVAL = 1.0  # seconds between requests


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


def _rate_limit_osrm():
    """Ensure we don't hit OSRM too frequently."""
    global _last_osrm_request
    elapsed = time.time() - _last_osrm_request
    if elapsed < OSRM_MIN_INTERVAL:
        time.sleep(OSRM_MIN_INTERVAL - elapsed)
    _last_osrm_request = time.time()


def get_osrm_route(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    profile: str = "cycling",
) -> Optional[dict]:
    """
    Get route from OSRM.

    Args:
        from_lat, from_lon: Origin coordinates
        to_lat, to_lon: Destination coordinates
        profile: "cycling", "driving", or "foot"

    Returns:
        dict with 'duration_min', 'distance_km', 'route_coords' or None on failure
    """
    _rate_limit_osrm()

    # OSRM uses lon,lat order (not lat,lon)
    url = (
        f"{OSRM_BASE_URL}/{profile}/{from_lon},{from_lat};{to_lon},{to_lat}"
        "?overview=full&geometries=geojson"
    )

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != "Ok" or not data.get("routes"):
                return None

            route = data["routes"][0]
            return {
                "duration_min": int(route["duration"] / 60),  # seconds to minutes
                "distance_km": round(route["distance"] / 1000, 2),  # meters to km
                "route_coords": route["geometry"]["coordinates"],  # [[lon,lat], ...]
            }
    except Exception as e:
        console.print(f"[yellow]OSRM request failed: {e}[/]")
        return None


def get_commute_routes(lat: float, lon: float) -> dict:
    """
    Get bike and driving commute times to work location via OSRM.

    Returns:
        dict with bike_min, driving_min, bike_route_coords, bike_distance_km
    """
    result = {
        "bike_min": None,
        "driving_min": None,
        "bike_route_coords": None,
        "bike_distance_km": None,
    }

    # Get bike route (with geometry for map display)
    bike_route = get_osrm_route(lat, lon, WORK_LAT, WORK_LNG, profile="cycling")
    if bike_route:
        result["bike_min"] = bike_route["duration_min"]
        result["bike_route_coords"] = bike_route["route_coords"]
        result["bike_distance_km"] = bike_route["distance_km"]

    # Get driving route (just duration, no geometry needed)
    driving_route = get_osrm_route(lat, lon, WORK_LAT, WORK_LNG, profile="driving")
    if driving_route:
        result["driving_min"] = driving_route["duration_min"]

    return result


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


def enrich_listing_with_geo(listing: dict, use_osrm: bool = True) -> dict:
    """
    Add geographic data to a listing.

    Args:
        listing: The listing dict to enrich
        use_osrm: If True, use OSRM API for real routing (slower but accurate).
                  If False, use simple distance-based estimates (faster).
    """
    # Try to get coordinates
    lat = listing.get("latitude")
    lon = listing.get("longitude")

    if not lat or not lon:
        # Try to geocode from address or postal code
        address = listing.get("address") or listing.get("title")
        postal = listing.get("postal_code")

        # Try different geocoding strategies
        coords = None

        # Strategy 1: Use postal code + Amsterdam (most reliable for NL)
        if postal and not coords:
            # Normalize postal code (remove spaces)
            postal_clean = postal.replace(" ", "")
            coords = geocode_address(f"{postal_clean}, Amsterdam")

        # Strategy 2: Use address directly (avoid adding postal if already present)
        if address and not coords:
            # Check if postal code is already in address
            if postal and postal.replace(" ", "") not in address.replace(" ", ""):
                address = f"{address}, {postal}"
            coords = geocode_address(address)

        if coords:
            listing["latitude"] = coords[0]
            listing["longitude"] = coords[1]
            lat, lon = coords

    # Calculate distance and commute times
    if lat and lon:
        # Always calculate straight-line distance
        distance = calculate_distance_to_work(lat, lon)
        listing["distance_km"] = round(distance, 2)

        if use_osrm:
            # Get real commute times via OSRM
            routes = get_commute_routes(lat, lon)
            if routes["bike_min"] is not None:
                listing["commute_time_bike_min"] = routes["bike_min"]
                listing["bike_route_coords"] = routes["bike_route_coords"]
            else:
                # Fallback to estimate
                bike_min, _ = estimate_commute_times(distance)
                listing["commute_time_bike_min"] = bike_min

            if routes["driving_min"] is not None:
                listing["commute_time_driving_min"] = routes["driving_min"]

            # Transit estimate (OSRM doesn't have transit, use heuristic)
            _, transit_min = estimate_commute_times(distance)
            listing["commute_time_transit_min"] = transit_min
        else:
            # Use simple estimates
            bike_min, transit_min = estimate_commute_times(distance)
            listing["commute_time_bike_min"] = bike_min
            listing["commute_time_transit_min"] = transit_min

    return listing
