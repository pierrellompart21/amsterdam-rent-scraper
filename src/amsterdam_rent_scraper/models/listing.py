"""Data models for rental listings."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RentalListing(BaseModel):
    """Structured rental listing extracted by LLM."""

    # === Identifiers ===
    source_site: str = Field(description="Website the listing was scraped from")
    listing_url: str = Field(description="Direct URL to the listing")
    raw_page_path: Optional[str] = Field(None, description="Path to saved raw HTML")
    scraped_at: datetime = Field(default_factory=datetime.now)

    # === Core details ===
    title: Optional[str] = None
    price_eur: Optional[float] = Field(None, description="Monthly rent in EUR")
    price_sek: Optional[float] = Field(None, description="Monthly rent in SEK (Swedish listings)")
    address: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # === Property details ===
    surface_m2: Optional[float] = None
    rooms: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    floor: Optional[str] = None
    furnished: Optional[str] = Field(
        None, description="Furnished / Unfurnished / Upholstered"
    )
    property_type: Optional[str] = Field(
        None, description="Apartment / Studio / House"
    )

    # === Conditions ===
    deposit_eur: Optional[float] = None
    available_date: Optional[str] = None
    minimum_contract_months: Optional[int] = None
    pets_allowed: Optional[str] = None
    smoking_allowed: Optional[str] = None
    energy_label: Optional[str] = None
    building_year: Optional[int] = None

    # === Landlord ===
    landlord_name: Optional[str] = None
    landlord_phone: Optional[str] = None
    agency: Optional[str] = None

    # === LLM analysis ===
    description_summary: Optional[str] = Field(
        None, description="LLM-generated summary of the listing"
    )
    pros: Optional[str] = Field(None, description="Positive aspects noted by LLM")
    cons: Optional[str] = Field(
        None, description="Negative aspects or red flags noted by LLM"
    )

    # === Commute (computed) ===
    distance_km: Optional[float] = Field(
        None, description="Straight-line distance to work"
    )
    commute_time_bike_min: Optional[int] = None
    commute_time_transit_min: Optional[int] = None
    commute_time_driving_min: Optional[int] = None
    # Route geometry for map display (GeoJSON coordinates)
    bike_route_coords: Optional[list] = Field(
        None, description="Bike route coordinates [[lon,lat], ...] for map display"
    )

    # === Neighborhood scores (computed) ===
    neighborhood_name: Optional[str] = Field(
        None, description="Identified neighborhood/district name"
    )
    neighborhood_safety: Optional[int] = Field(None, description="Safety score 1-10")
    neighborhood_green_space: Optional[int] = Field(
        None, description="Green space score 1-10"
    )
    neighborhood_amenities: Optional[int] = Field(
        None, description="Amenities score 1-10"
    )
    neighborhood_restaurants: Optional[int] = Field(
        None, description="Restaurants score 1-10"
    )
    neighborhood_family_friendly: Optional[int] = Field(
        None, description="Family friendliness score 1-10"
    )
    neighborhood_expat_friendly: Optional[int] = Field(
        None, description="Expat friendliness score 1-10"
    )
    neighborhood_overall: Optional[float] = Field(
        None, description="Weighted overall neighborhood score"
    )
