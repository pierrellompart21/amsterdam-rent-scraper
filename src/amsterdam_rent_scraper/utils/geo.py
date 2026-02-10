"""Geographic utilities for distance and commute calculations."""

import math
import time
from typing import Optional, Tuple

import httpx
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from rich.console import Console

from amsterdam_rent_scraper.config.settings import (
    DEFAULT_CITY,
    WORK_LAT,
    WORK_LNG,
    get_city_config,
)
from amsterdam_rent_scraper.utils.neighborhoods import enrich_listing_with_neighborhood

console = Console()

# Initialize geocoder
geolocator = Nominatim(user_agent="rent_scraper")

# OSRM public demo server (free, no API key required)
OSRM_BASE_URL = "http://router.project-osrm.org/route/v1"

# Transitous API (MOTIS-based, free public transit routing for Netherlands and other EU countries)
TRANSITOUS_BASE_URL = "https://api.transitous.org/api/v1"

# HSL Digitransit API (Helsinki Region Transport - free GraphQL API)
HSL_DIGITRANSIT_URL = "https://api.digitransit.fi/routing/v1/routers/hsl/index/graphql"

# Rate limiting for APIs (be respectful to free services)
_last_osrm_request = 0.0
OSRM_MIN_INTERVAL = 1.0  # seconds between requests

_last_transitous_request = 0.0
TRANSITOUS_MIN_INTERVAL = 1.0  # seconds between requests

_last_hsl_request = 0.0
HSL_MIN_INTERVAL = 0.5  # HSL allows more frequent requests


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


def geocode_address(address: str, city: str = None) -> Optional[Tuple[float, float]]:
    """Geocode an address to latitude/longitude coordinates."""
    if not address:
        return None

    city_config = get_city_config(city) if city else get_city_config(DEFAULT_CITY)

    # Add country if not present
    country_lower = city_config.country.lower()
    if country_lower not in address.lower():
        # Also check for common abbreviations
        country_abbrevs = {
            "netherlands": ["nl", "nederland"],
            "finland": ["fi", "suomi"],
            "sweden": ["se", "sverige"],
        }
        abbrevs = country_abbrevs.get(country_lower, [])
        if not any(abbrev in address.lower() for abbrev in abbrevs):
            address = f"{address}, {city_config.country}"

    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return (location.latitude, location.longitude)
    except GeocoderTimedOut:
        console.print(f"[yellow]Geocoding timed out for: {address}[/]")
    except Exception as e:
        console.print(f"[yellow]Geocoding failed for {address}: {e}[/]")

    return None


def calculate_distance_to_work(lat: float, lon: float, city: str = None) -> float:
    """Calculate distance from a point to the work location."""
    city_config = get_city_config(city) if city else get_city_config(DEFAULT_CITY)
    return haversine_distance(lat, lon, city_config.work_lat, city_config.work_lng)


def _rate_limit_osrm():
    """Ensure we don't hit OSRM too frequently."""
    global _last_osrm_request
    elapsed = time.time() - _last_osrm_request
    if elapsed < OSRM_MIN_INTERVAL:
        time.sleep(OSRM_MIN_INTERVAL - elapsed)
    _last_osrm_request = time.time()


def _rate_limit_transitous():
    """Ensure we don't hit Transitous API too frequently."""
    global _last_transitous_request
    elapsed = time.time() - _last_transitous_request
    if elapsed < TRANSITOUS_MIN_INTERVAL:
        time.sleep(TRANSITOUS_MIN_INTERVAL - elapsed)
    _last_transitous_request = time.time()


def _rate_limit_hsl():
    """Ensure we don't hit HSL API too frequently."""
    global _last_hsl_request
    elapsed = time.time() - _last_hsl_request
    if elapsed < HSL_MIN_INTERVAL:
        time.sleep(HSL_MIN_INTERVAL - elapsed)
    _last_hsl_request = time.time()


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


def get_transit_route_transitous(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> Optional[dict]:
    """
    Get public transit route from Transitous (MOTIS API).
    Works for Netherlands and other EU countries.

    Args:
        from_lat, from_lon: Origin coordinates
        to_lat, to_lon: Destination coordinates

    Returns:
        dict with 'duration_min', 'transfers' or None on failure
    """
    _rate_limit_transitous()

    # Don't specify a time - the API defaults to "now" which ensures
    # we get valid routes based on current GTFS data
    url = (
        f"{TRANSITOUS_BASE_URL}/plan?"
        f"fromPlace={from_lat},{from_lon}&"
        f"toPlace={to_lat},{to_lon}&"
        f"directModes=WALK&"
        f"transitModes=TRANSIT"
    )

    headers = {
        "User-Agent": "RentScraper/1.0 (https://github.com/pierre/rent-scraper)"
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

            itineraries = data.get("itineraries", [])
            if not itineraries:
                return None

            # Find the best itinerary (shortest duration with fewest transfers)
            # Sort by duration, then by transfers
            sorted_itineraries = sorted(
                itineraries,
                key=lambda x: (x.get("duration", 99999), x.get("transfers", 99))
            )
            best = sorted_itineraries[0]

            return {
                "duration_min": int(best["duration"] / 60),  # seconds to minutes
                "transfers": best.get("transfers", 0),
            }
    except Exception as e:
        console.print(f"[yellow]Transitous request failed: {e}[/]")
        return None


def get_transit_route_hsl(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
) -> Optional[dict]:
    """
    Get public transit route from HSL Digitransit API (Helsinki Region).
    Uses GraphQL API for real transit routing with metro/tram/bus.

    Args:
        from_lat, from_lon: Origin coordinates
        to_lat, to_lon: Destination coordinates

    Returns:
        dict with 'duration_min', 'transfers' or None on failure
    """
    _rate_limit_hsl()

    # GraphQL query for route planning
    query = """
    {
      plan(
        from: {lat: %f, lon: %f}
        to: {lat: %f, lon: %f}
        numItineraries: 3
        transportModes: [
          {mode: WALK}
          {mode: TRANSIT}
        ]
      ) {
        itineraries {
          duration
          legs {
            mode
          }
        }
      }
    }
    """ % (from_lat, from_lon, to_lat, to_lon)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "RentScraper/1.0",
        "digitransit-subscription-key": "5cc1e3273e3943438a35e65d8cad7ac8",  # Public test key
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                HSL_DIGITRANSIT_URL,
                json={"query": query},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

            plan = data.get("data", {}).get("plan", {})
            itineraries = plan.get("itineraries", [])
            if not itineraries:
                return None

            # Find the best itinerary (shortest duration)
            best = min(itineraries, key=lambda x: x.get("duration", 99999))

            # Count transfers (non-WALK legs minus 1)
            transit_legs = [leg for leg in best.get("legs", []) if leg.get("mode") != "WALK"]
            transfers = max(0, len(transit_legs) - 1)

            return {
                "duration_min": int(best["duration"] / 60),  # seconds to minutes
                "transfers": transfers,
            }
    except Exception as e:
        console.print(f"[yellow]HSL Digitransit request failed: {e}[/]")
        return None


def get_transit_route(
    from_lat: float,
    from_lon: float,
    to_lat: float,
    to_lon: float,
    city: str = None,
) -> Optional[dict]:
    """
    Get public transit route using city-appropriate API.

    Args:
        from_lat, from_lon: Origin coordinates
        to_lat, to_lon: Destination coordinates
        city: City name to determine which API to use

    Returns:
        dict with 'duration_min', 'transfers' or None on failure
    """
    # For now, use Transitous for all cities (it covers both NL and FI)
    # HSL Digitransit API requires a subscription key since 2024
    # Transitous provides good coverage for Helsinki region as well
    return get_transit_route_transitous(from_lat, from_lon, to_lat, to_lon)


def get_commute_routes(lat: float, lon: float, city: str = None) -> dict:
    """
    Get bike, driving, and transit commute times to work location.

    Returns:
        dict with bike_min, driving_min, transit_min, bike_route_coords, bike_distance_km, transit_transfers
    """
    city_config = get_city_config(city) if city else get_city_config(DEFAULT_CITY)
    work_lat = city_config.work_lat
    work_lng = city_config.work_lng

    result = {
        "bike_min": None,
        "driving_min": None,
        "transit_min": None,
        "transit_transfers": None,
        "bike_route_coords": None,
        "bike_distance_km": None,
    }

    # Get bike route (with geometry for map display)
    bike_route = get_osrm_route(lat, lon, work_lat, work_lng, profile="cycling")
    if bike_route:
        result["bike_min"] = bike_route["duration_min"]
        result["bike_route_coords"] = bike_route["route_coords"]
        result["bike_distance_km"] = bike_route["distance_km"]

    # Get driving route (just duration, no geometry needed)
    driving_route = get_osrm_route(lat, lon, work_lat, work_lng, profile="driving")
    if driving_route:
        result["driving_min"] = driving_route["duration_min"]

    # Get transit route via city-appropriate API
    transit_route = get_transit_route(lat, lon, work_lat, work_lng, city=city)
    if transit_route:
        result["transit_min"] = transit_route["duration_min"]
        result["transit_transfers"] = transit_route["transfers"]

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


def enrich_listing_with_geo(listing: dict, use_osrm: bool = True, city: str = None) -> dict:
    """
    Add geographic data to a listing.

    Args:
        listing: The listing dict to enrich
        use_osrm: If True, use OSRM API for real routing (slower but accurate).
                  If False, use simple distance-based estimates (faster).
        city: City name for city-specific geocoding and routing
    """
    city_config = get_city_config(city) if city else get_city_config(DEFAULT_CITY)

    # Try to get coordinates
    lat = listing.get("latitude")
    lon = listing.get("longitude")

    if not lat or not lon:
        # Try to geocode from address or postal code
        address = listing.get("address") or listing.get("title")
        postal = listing.get("postal_code")

        # Try different geocoding strategies
        coords = None

        # Strategy 1: Use postal code + city name (most reliable)
        if postal and not coords:
            # Normalize postal code (remove spaces)
            postal_clean = postal.replace(" ", "")
            coords = geocode_address(f"{postal_clean}, {city_config.name}", city=city)

        # Strategy 2: Use address directly (avoid adding postal if already present)
        if address and not coords:
            # Check if postal code is already in address
            if postal and postal.replace(" ", "") not in address.replace(" ", ""):
                address = f"{address}, {postal}"
            coords = geocode_address(address, city=city)

        if coords:
            listing["latitude"] = coords[0]
            listing["longitude"] = coords[1]
            lat, lon = coords

    # Calculate distance and commute times
    if lat and lon:
        # Always calculate straight-line distance
        distance = calculate_distance_to_work(lat, lon, city=city)
        listing["distance_km"] = round(distance, 2)

        if use_osrm:
            # Get real commute times via OSRM and city-appropriate transit API
            routes = get_commute_routes(lat, lon, city=city)
            if routes["bike_min"] is not None:
                listing["commute_time_bike_min"] = routes["bike_min"]
                listing["bike_route_coords"] = routes["bike_route_coords"]
            else:
                # Fallback to estimate
                bike_min, _ = estimate_commute_times(distance)
                listing["commute_time_bike_min"] = bike_min

            if routes["driving_min"] is not None:
                listing["commute_time_driving_min"] = routes["driving_min"]

            # Transit via city-appropriate API or fallback to heuristic
            if routes["transit_min"] is not None:
                listing["commute_time_transit_min"] = routes["transit_min"]
                listing["transit_transfers"] = routes["transit_transfers"]
            else:
                # Fallback to heuristic if API fails
                _, transit_min = estimate_commute_times(distance)
                listing["commute_time_transit_min"] = transit_min
        else:
            # Use simple estimates
            bike_min, transit_min = estimate_commute_times(distance)
            listing["commute_time_bike_min"] = bike_min
            listing["commute_time_transit_min"] = transit_min

    # Add neighborhood quality scores (city-specific)
    enrich_listing_with_neighborhood(listing, city=city)

    return listing
