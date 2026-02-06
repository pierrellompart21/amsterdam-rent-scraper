"""Amsterdam neighborhood quality scores.

Hardcoded ratings for Amsterdam districts and nearby municipalities.
Scores are 1-10 for various quality metrics.
"""

from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class NeighborhoodScores:
    """Quality scores for a neighborhood (1-10 scale)."""

    name: str
    safety: int
    green_space: int
    amenities: int
    restaurants: int
    family_friendly: int
    expat_friendly: int

    @property
    def overall(self) -> float:
        """Calculate weighted overall score."""
        return round(
            (
                self.safety * 1.5
                + self.green_space * 1.0
                + self.amenities * 1.2
                + self.restaurants * 0.8
                + self.family_friendly * 1.0
                + self.expat_friendly * 1.0
            )
            / 6.5,  # sum of weights
            1,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "safety": self.safety,
            "green_space": self.green_space,
            "amenities": self.amenities,
            "restaurants": self.restaurants,
            "family_friendly": self.family_friendly,
            "expat_friendly": self.expat_friendly,
            "overall": self.overall,
        }


# Amsterdam district ratings
# Based on general reputation, expat guides, and livability rankings
NEIGHBORHOOD_DATA: dict[str, NeighborhoodScores] = {
    # === Amsterdam City Districts ===
    "centrum": NeighborhoodScores(
        name="Centrum",
        safety=6,  # Tourists, petty crime
        green_space=4,  # Very urban, few parks
        amenities=10,  # Everything available
        restaurants=10,  # Best dining scene
        family_friendly=4,  # Crowded, noisy
        expat_friendly=9,  # Very international
    ),
    "oud-west": NeighborhoodScores(
        name="Oud-West",
        safety=8,
        green_space=6,  # Vondelpark nearby
        amenities=9,
        restaurants=9,  # Great food scene
        family_friendly=7,
        expat_friendly=9,
    ),
    "de pijp": NeighborhoodScores(
        name="De Pijp",
        safety=8,
        green_space=5,  # Sarphatipark
        amenities=9,
        restaurants=9,  # Albert Cuyp market area
        family_friendly=6,
        expat_friendly=9,
    ),
    "zuid": NeighborhoodScores(
        name="Zuid",
        safety=9,
        green_space=8,  # Vondelpark, Beatrixpark
        amenities=9,
        restaurants=8,
        family_friendly=9,  # Very family-oriented
        expat_friendly=10,  # Many international schools
    ),
    "oud-zuid": NeighborhoodScores(
        name="Oud-Zuid",
        safety=9,
        green_space=8,
        amenities=9,
        restaurants=8,
        family_friendly=9,
        expat_friendly=10,
    ),
    "rivierenbuurt": NeighborhoodScores(
        name="Rivierenbuurt",
        safety=8,
        green_space=7,
        amenities=7,
        restaurants=6,
        family_friendly=8,
        expat_friendly=7,
    ),
    "buitenveldert": NeighborhoodScores(
        name="Buitenveldert",
        safety=9,
        green_space=8,
        amenities=7,
        restaurants=5,
        family_friendly=9,
        expat_friendly=8,  # Near Zuidas
    ),
    "oost": NeighborhoodScores(
        name="Oost",
        safety=7,
        green_space=8,  # Oosterpark, Flevopark
        amenities=8,
        restaurants=8,
        family_friendly=7,
        expat_friendly=8,
    ),
    "watergraafsmeer": NeighborhoodScores(
        name="Watergraafsmeer",
        safety=8,
        green_space=8,  # Flevopark, Frankendael
        amenities=6,
        restaurants=5,
        family_friendly=9,
        expat_friendly=6,
    ),
    "west": NeighborhoodScores(
        name="West",
        safety=7,
        green_space=6,  # Westerpark, Erasmuspark
        amenities=8,
        restaurants=8,
        family_friendly=7,
        expat_friendly=8,
    ),
    "westerpark": NeighborhoodScores(
        name="Westerpark",
        safety=7,
        green_space=8,  # Large Westerpark
        amenities=7,
        restaurants=7,
        family_friendly=7,
        expat_friendly=7,
    ),
    "jordaan": NeighborhoodScores(
        name="Jordaan",
        safety=8,
        green_space=4,  # Very urban
        amenities=8,
        restaurants=9,
        family_friendly=5,  # Small apartments
        expat_friendly=8,
    ),
    "noord": NeighborhoodScores(
        name="Noord",
        safety=7,
        green_space=9,  # Very green, rural areas
        amenities=6,  # Developing
        restaurants=6,  # NDSM, growing scene
        family_friendly=8,
        expat_friendly=6,
    ),
    "nieuw-west": NeighborhoodScores(
        name="Nieuw-West",
        safety=6,
        green_space=7,  # Sloterpark, Sloterplas
        amenities=6,
        restaurants=5,
        family_friendly=7,
        expat_friendly=5,
    ),
    "slotermeer": NeighborhoodScores(
        name="Slotermeer",
        safety=5,
        green_space=7,
        amenities=5,
        restaurants=4,
        family_friendly=6,
        expat_friendly=4,
    ),
    "geuzenveld": NeighborhoodScores(
        name="Geuzenveld",
        safety=5,
        green_space=7,
        amenities=5,
        restaurants=4,
        family_friendly=6,
        expat_friendly=4,
    ),
    "zuidoost": NeighborhoodScores(
        name="Zuidoost",
        safety=5,  # Bijlmer area reputation
        green_space=7,  # Gaasperpark
        amenities=6,  # Arena area
        restaurants=5,
        family_friendly=6,
        expat_friendly=5,
    ),
    "ijburg": NeighborhoodScores(
        name="IJburg",
        safety=8,
        green_space=7,  # Water, beaches
        amenities=5,  # Still developing
        restaurants=4,
        family_friendly=9,  # Designed for families
        expat_friendly=6,
    ),
    "zuidas": NeighborhoodScores(
        name="Zuidas",
        safety=9,
        green_space=5,
        amenities=7,  # Business district
        restaurants=7,
        family_friendly=5,  # More business-oriented
        expat_friendly=10,  # International business hub
    ),
    # === Nearby Municipalities ===
    "amstelveen": NeighborhoodScores(
        name="Amstelveen",
        safety=9,
        green_space=9,  # Amsterdamse Bos
        amenities=8,
        restaurants=7,
        family_friendly=10,  # Very family-oriented
        expat_friendly=10,  # Large expat community, international schools
    ),
    "diemen": NeighborhoodScores(
        name="Diemen",
        safety=8,
        green_space=7,
        amenities=6,
        restaurants=5,
        family_friendly=8,
        expat_friendly=6,
    ),
    "duivendrecht": NeighborhoodScores(
        name="Duivendrecht",
        safety=7,
        green_space=6,
        amenities=5,
        restaurants=4,
        family_friendly=7,
        expat_friendly=5,
    ),
    "ouder-amstel": NeighborhoodScores(
        name="Ouder-Amstel",
        safety=8,
        green_space=8,
        amenities=5,
        restaurants=4,
        family_friendly=8,
        expat_friendly=5,
    ),
    "haarlem": NeighborhoodScores(
        name="Haarlem",
        safety=8,
        green_space=7,
        amenities=8,
        restaurants=8,
        family_friendly=8,
        expat_friendly=7,
    ),
    "hoofddorp": NeighborhoodScores(
        name="Hoofddorp",
        safety=8,
        green_space=7,
        amenities=7,
        restaurants=5,
        family_friendly=8,
        expat_friendly=6,
    ),
    "zaandam": NeighborhoodScores(
        name="Zaandam",
        safety=6,
        green_space=7,
        amenities=6,
        restaurants=5,
        family_friendly=7,
        expat_friendly=4,
    ),
    "almere": NeighborhoodScores(
        name="Almere",
        safety=7,
        green_space=8,
        amenities=7,
        restaurants=5,
        family_friendly=8,
        expat_friendly=4,
    ),
    "purmerend": NeighborhoodScores(
        name="Purmerend",
        safety=7,
        green_space=7,
        amenities=6,
        restaurants=4,
        family_friendly=8,
        expat_friendly=3,
    ),
    "hilversum": NeighborhoodScores(
        name="Hilversum",
        safety=8,
        green_space=9,
        amenities=7,
        restaurants=6,
        family_friendly=8,
        expat_friendly=6,
    ),
    "uithoorn": NeighborhoodScores(
        name="Uithoorn",
        safety=8,
        green_space=8,
        amenities=5,
        restaurants=4,
        family_friendly=8,
        expat_friendly=4,
    ),
    "abcoude": NeighborhoodScores(
        name="Abcoude",
        safety=9,
        green_space=9,
        amenities=4,
        restaurants=4,
        family_friendly=8,
        expat_friendly=4,
    ),
}

# Alternative name mappings for neighborhood detection
NEIGHBORHOOD_ALIASES: dict[str, str] = {
    # Centrum variations
    "city center": "centrum",
    "binnenstad": "centrum",
    "red light district": "centrum",
    "de wallen": "centrum",
    "grachtengordel": "centrum",
    "canal belt": "centrum",
    # Zuid variations
    "amsterdam-zuid": "zuid",
    "amsterdam zuid": "zuid",
    "museumkwartier": "zuid",
    "museum quarter": "zuid",
    "apollobuurt": "zuid",
    "stadionbuurt": "zuid",
    # Oud-West variations
    "oud west": "oud-west",
    "oude west": "oud-west",
    # De Pijp variations
    "pijp": "de pijp",
    "the pijp": "de pijp",
    # Oost variations
    "amsterdam-oost": "oost",
    "amsterdam oost": "oost",
    "indische buurt": "oost",
    "dapperbuurt": "oost",
    "transvaalbuurt": "oost",
    "oosterparkbuurt": "oost",
    # West variations
    "amsterdam-west": "west",
    "amsterdam west": "west",
    "de baarsjes": "west",
    "bos en lommer": "west",
    # Noord variations
    "amsterdam-noord": "noord",
    "amsterdam noord": "noord",
    "ndsm": "noord",
    "buiksloterham": "noord",
    "nieuwendam": "noord",
    # Nieuw-West variations
    "nieuw west": "nieuw-west",
    "amsterdam nieuw-west": "nieuw-west",
    "osdorp": "nieuw-west",
    "slotervaart": "nieuw-west",
    # Zuidoost variations
    "zuid-oost": "zuidoost",
    "amsterdam-zuidoost": "zuidoost",
    "amsterdam zuidoost": "zuidoost",
    "bijlmer": "zuidoost",
    "bijlmermeer": "zuidoost",
    "holendrecht": "zuidoost",
    "gaasperdam": "zuidoost",
    "arena": "zuidoost",
    # Other
    "vondelpark": "oud-west",
    "amstel": "rivierenbuurt",
    "science park": "watergraafsmeer",
}


def normalize_neighborhood_name(name: str) -> str:
    """Normalize a neighborhood name for lookup."""
    if not name:
        return ""
    # Lowercase and strip
    normalized = name.lower().strip()
    # Remove common prefixes
    for prefix in ["amsterdam ", "amsterdam-"]:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return normalized


def identify_neighborhood(
    address: str = None,
    city: str = None,
    neighborhood: str = None,
    postal_code: str = None,
) -> Optional[str]:
    """
    Identify the neighborhood from address components.

    Returns the normalized neighborhood key or None if not identified.
    """
    # Check for non-Amsterdam municipalities first (by city name)
    if city:
        city_lower = city.lower().strip()
        # Direct municipality matches
        non_amsterdam_cities = [
            "amstelveen", "diemen", "duivendrecht", "ouder-amstel",
            "haarlem", "hoofddorp", "zaandam", "almere", "purmerend",
            "hilversum", "uithoorn", "abcoude"
        ]
        for muni in non_amsterdam_cities:
            if muni in city_lower or city_lower == muni:
                if muni in NEIGHBORHOOD_DATA:
                    return muni

    # Build search text from all available fields
    search_parts = []
    if neighborhood:
        search_parts.append(neighborhood.lower())
    if city:
        search_parts.append(city.lower())
    if address:
        search_parts.append(address.lower())

    search_text = " ".join(search_parts)

    # Try direct match in aliases first
    for alias, key in NEIGHBORHOOD_ALIASES.items():
        if alias in search_text:
            return key

    # Try direct neighborhood name match (but skip partial matches like "amstel" in "amstelveen")
    for key in NEIGHBORHOOD_DATA.keys():
        # Skip municipality names (already checked above)
        if key in ["amstelveen", "diemen", "duivendrecht", "ouder-amstel",
                   "haarlem", "hoofddorp", "zaandam", "almere", "purmerend",
                   "hilversum", "uithoorn", "abcoude"]:
            continue
        # Check if the neighborhood name appears in the text
        if key in search_text or key.replace("-", " ") in search_text:
            return key

    # Try postal code heuristic for Amsterdam area
    if postal_code:
        postal_clean = postal_code.replace(" ", "").upper()
        postal_match = re.match(r"(\d{4})", postal_clean)
        if postal_match:
            postal_num = int(postal_match.group(1))

            # Amsterdam postal code ranges (approximate)
            # Order matters - more specific ranges first!

            # Centrum (1011-1018)
            if 1011 <= postal_num <= 1018:
                return "centrum"

            # Eastern docks
            elif postal_num == 1019:
                return "oost"

            # Noord (1020-1039, 1090-1099)
            elif 1020 <= postal_num <= 1039:
                return "noord"
            elif 1090 <= postal_num <= 1099:
                return "noord"

            # Oud-West (1051-1055) - check before broader west range
            elif 1051 <= postal_num <= 1055:
                return "oud-west"

            # West (1056-1059)
            elif 1056 <= postal_num <= 1059:
                return "west"

            # Nieuw-West (1040-1049, 1060-1069)
            elif 1040 <= postal_num <= 1049:
                return "nieuw-west"
            elif 1060 <= postal_num <= 1069:
                return "nieuw-west"

            # Zuid (1071-1079)
            elif 1071 <= postal_num <= 1079:
                return "zuid"

            # Buitenveldert/Zuidas (1081-1083)
            elif 1081 <= postal_num <= 1083:
                return "buitenveldert"

            # Nieuw-West (1080, 1084-1089)
            elif 1080 <= postal_num <= 1089:
                return "nieuw-west"

            # Oost (1091-1098)
            elif 1091 <= postal_num <= 1098:
                return "oost"

            # Zuidoost (1100-1109)
            elif 1100 <= postal_num <= 1109:
                return "zuidoost"

            # Diemen (1110-1119)
            elif 1110 <= postal_num <= 1119:
                return "diemen"

            # Amstelveen (1180-1189)
            elif 1180 <= postal_num <= 1189:
                return "amstelveen"

    return None


def get_neighborhood_scores(
    address: str = None,
    city: str = None,
    neighborhood: str = None,
    postal_code: str = None,
) -> Optional[NeighborhoodScores]:
    """
    Get neighborhood scores for a location.

    Returns NeighborhoodScores if the neighborhood can be identified, None otherwise.
    """
    key = identify_neighborhood(address, city, neighborhood, postal_code)
    if key and key in NEIGHBORHOOD_DATA:
        return NEIGHBORHOOD_DATA[key]
    return None


def enrich_listing_with_neighborhood(listing: dict) -> dict:
    """
    Add neighborhood quality scores to a listing.

    Modifies the listing dict in place and returns it.
    """
    scores = get_neighborhood_scores(
        address=listing.get("address"),
        city=listing.get("city"),
        neighborhood=listing.get("neighborhood"),
        postal_code=listing.get("postal_code"),
    )

    if scores:
        listing["neighborhood_name"] = scores.name
        listing["neighborhood_safety"] = scores.safety
        listing["neighborhood_green_space"] = scores.green_space
        listing["neighborhood_amenities"] = scores.amenities
        listing["neighborhood_restaurants"] = scores.restaurants
        listing["neighborhood_family_friendly"] = scores.family_friendly
        listing["neighborhood_expat_friendly"] = scores.expat_friendly
        listing["neighborhood_overall"] = scores.overall

    return listing
