"""City neighborhood quality scores.

Hardcoded ratings for districts in supported cities.
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

# === HELSINKI (Finland) district ratings ===
# Based on livability data, expat guides, and local reputation
HELSINKI_NEIGHBORHOOD_DATA: dict[str, NeighborhoodScores] = {
    # === Central Helsinki ===
    "kallio": NeighborhoodScores(
        name="Kallio",
        safety=7,  # Trendy but some nightlife noise
        green_space=5,  # Urban, but parks nearby
        amenities=9,  # Excellent shops, bars, cafes
        restaurants=9,  # Vibrant food scene
        family_friendly=5,  # More young professionals
        expat_friendly=8,  # Popular with expats
    ),
    "kamppi": NeighborhoodScores(
        name="Kamppi",
        safety=8,
        green_space=4,  # Very urban, shopping center
        amenities=10,  # Major shopping hub
        restaurants=9,
        family_friendly=5,
        expat_friendly=9,
    ),
    "punavuori": NeighborhoodScores(
        name="Punavuori",
        safety=9,
        green_space=5,
        amenities=9,  # Design district
        restaurants=10,  # Best restaurants
        family_friendly=6,
        expat_friendly=9,
    ),
    "ullanlinna": NeighborhoodScores(
        name="Ullanlinna",
        safety=9,
        green_space=7,  # Near sea, Kaivopuisto
        amenities=8,
        restaurants=8,
        family_friendly=8,
        expat_friendly=9,  # Diplomatic area
    ),
    "töölö": NeighborhoodScores(
        name="Töölö",
        safety=9,
        green_space=8,  # Near Töölönlahti bay
        amenities=8,
        restaurants=7,
        family_friendly=9,
        expat_friendly=8,
    ),
    "kruununhaka": NeighborhoodScores(
        name="Kruununhaka",
        safety=9,
        green_space=5,  # Historic center
        amenities=8,
        restaurants=7,
        family_friendly=7,
        expat_friendly=8,
    ),
    # === Eastern Helsinki ===
    "sörnäinen": NeighborhoodScores(
        name="Sörnäinen",
        safety=6,  # Developing area
        green_space=5,
        amenities=7,
        restaurants=7,
        family_friendly=5,
        expat_friendly=6,
    ),
    "vallila": NeighborhoodScores(
        name="Vallila",
        safety=8,
        green_space=6,
        amenities=7,
        restaurants=6,
        family_friendly=7,
        expat_friendly=7,
    ),
    "pasila": NeighborhoodScores(
        name="Pasila",
        safety=7,
        green_space=5,  # Rail hub area
        amenities=7,
        restaurants=5,
        family_friendly=6,
        expat_friendly=6,
    ),
    "arabia": NeighborhoodScores(
        name="Arabia",
        safety=8,
        green_space=7,  # Near Vanhankaupunginlahti
        amenities=7,
        restaurants=6,
        family_friendly=8,
        expat_friendly=7,
    ),
    "herttoniemi": NeighborhoodScores(
        name="Herttoniemi",
        safety=8,
        green_space=8,  # Nature areas
        amenities=6,
        restaurants=5,
        family_friendly=8,
        expat_friendly=6,
    ),
    "kulosaari": NeighborhoodScores(
        name="Kulosaari",
        safety=9,
        green_space=9,  # Island community
        amenities=5,
        restaurants=4,
        family_friendly=9,
        expat_friendly=7,
    ),
    "vuosaari": NeighborhoodScores(
        name="Vuosaari",
        safety=6,
        green_space=8,  # Beach, nature
        amenities=7,
        restaurants=5,
        family_friendly=7,
        expat_friendly=5,
    ),
    "kontula": NeighborhoodScores(
        name="Kontula",
        safety=5,  # More affordable but less safe
        green_space=7,
        amenities=6,
        restaurants=5,
        family_friendly=6,
        expat_friendly=4,
    ),
    "malmi": NeighborhoodScores(
        name="Malmi",
        safety=6,
        green_space=7,
        amenities=7,
        restaurants=5,
        family_friendly=7,
        expat_friendly=5,
    ),
    # === Northern Helsinki ===
    "oulunkylä": NeighborhoodScores(
        name="Oulunkylä",
        safety=8,
        green_space=8,
        amenities=6,
        restaurants=5,
        family_friendly=9,
        expat_friendly=6,
    ),
    "käpylä": NeighborhoodScores(
        name="Käpylä",
        safety=9,
        green_space=8,  # Garden city
        amenities=6,
        restaurants=5,
        family_friendly=9,
        expat_friendly=7,
    ),
    # === Western Helsinki ===
    "munkkiniemi": NeighborhoodScores(
        name="Munkkiniemi",
        safety=9,
        green_space=9,  # Near Central Park
        amenities=7,
        restaurants=6,
        family_friendly=9,
        expat_friendly=8,
    ),
    "lauttasaari": NeighborhoodScores(
        name="Lauttasaari",
        safety=9,
        green_space=8,  # Island, beaches
        amenities=8,
        restaurants=7,
        family_friendly=9,
        expat_friendly=8,
    ),
    "jätkäsaari": NeighborhoodScores(
        name="Jätkäsaari",
        safety=9,
        green_space=6,  # New development
        amenities=7,
        restaurants=7,
        family_friendly=8,
        expat_friendly=8,
    ),
    "ruoholahti": NeighborhoodScores(
        name="Ruoholahti",
        safety=9,
        green_space=6,  # Near water
        amenities=8,
        restaurants=7,
        family_friendly=7,
        expat_friendly=8,
    ),
    # === Espoo (Western Greater Helsinki) ===
    "tapiola": NeighborhoodScores(
        name="Tapiola",
        safety=9,
        green_space=9,  # Garden city design
        amenities=9,  # Major center
        restaurants=7,
        family_friendly=9,
        expat_friendly=9,  # Many tech companies
    ),
    "otaniemi": NeighborhoodScores(
        name="Otaniemi",
        safety=9,
        green_space=8,  # Aalto campus
        amenities=6,
        restaurants=5,
        family_friendly=6,
        expat_friendly=9,  # University, tech hub
    ),
    "leppävaara": NeighborhoodScores(
        name="Leppävaara",
        safety=8,
        green_space=7,
        amenities=9,  # Sello mall
        restaurants=6,
        family_friendly=8,
        expat_friendly=7,
    ),
    "matinkylä": NeighborhoodScores(
        name="Matinkylä",
        safety=8,
        green_space=7,
        amenities=8,  # Iso Omena mall
        restaurants=6,
        family_friendly=8,
        expat_friendly=7,
    ),
    "keilaniemi": NeighborhoodScores(
        name="Keilaniemi",
        safety=9,
        green_space=7,  # Waterfront, near nature
        amenities=6,  # Business district
        restaurants=6,
        family_friendly=5,  # More offices
        expat_friendly=10,  # Tech headquarters (Microsoft, Nokia, etc.)
    ),
    "espoo center": NeighborhoodScores(
        name="Espoo Center",
        safety=8,
        green_space=7,
        amenities=8,
        restaurants=6,
        family_friendly=8,
        expat_friendly=7,
    ),
}

# === STOCKHOLM (Sweden) district ratings ===
# Based on livability data, expat guides, and local reputation
STOCKHOLM_NEIGHBORHOOD_DATA: dict[str, NeighborhoodScores] = {
    # === Central Stockholm (Innerstaden) ===
    "norrmalm": NeighborhoodScores(
        name="Norrmalm",
        safety=8,
        green_space=5,  # Urban center, Kungsträdgården
        amenities=10,  # Shopping, dining, transport hub
        restaurants=10,  # Best selection
        family_friendly=5,  # Busy commercial area
        expat_friendly=10,  # Very international
    ),
    "östermalm": NeighborhoodScores(
        name="Östermalm",
        safety=9,
        green_space=7,  # Humlegården, Djurgården nearby
        amenities=9,
        restaurants=9,  # High-end dining
        family_friendly=8,
        expat_friendly=10,  # Most international neighborhood
    ),
    "södermalm": NeighborhoodScores(
        name="Södermalm",
        safety=8,
        green_space=6,  # Tantolunden, Vitabergsparken
        amenities=9,
        restaurants=9,  # Trendy bars and restaurants
        family_friendly=6,  # Young, hip area
        expat_friendly=9,
    ),
    "vasastan": NeighborhoodScores(
        name="Vasastan",
        safety=9,
        green_space=6,  # Vasaparken
        amenities=8,
        restaurants=8,
        family_friendly=8,
        expat_friendly=8,
    ),
    "kungsholmen": NeighborhoodScores(
        name="Kungsholmen",
        safety=9,
        green_space=8,  # Rålambshovsparken, waterfront
        amenities=8,
        restaurants=7,
        family_friendly=9,
        expat_friendly=8,
    ),
    "gamla stan": NeighborhoodScores(
        name="Gamla Stan",
        safety=8,  # Touristy
        green_space=3,  # Historic, no parks
        amenities=7,
        restaurants=8,
        family_friendly=5,  # Small apartments, crowded
        expat_friendly=7,
    ),
    "djurgården": NeighborhoodScores(
        name="Djurgården",
        safety=9,
        green_space=10,  # Royal park, nature
        amenities=5,  # Mainly museums/attractions
        restaurants=5,
        family_friendly=9,  # Great for families
        expat_friendly=7,
    ),
    # === Söderort (Southern suburbs) ===
    "hammarby sjöstad": NeighborhoodScores(
        name="Hammarby Sjöstad",
        safety=9,
        green_space=8,  # Modern eco-district, waterfront
        amenities=7,
        restaurants=6,
        family_friendly=9,
        expat_friendly=8,
    ),
    # === Eastern areas ===
    "gärdet": NeighborhoodScores(
        name="Gärdet",
        safety=9,
        green_space=9,  # Open fields, Ladugårdsgärde
        amenities=6,
        restaurants=5,
        family_friendly=9,
        expat_friendly=7,
    ),
    "hjorthagen": NeighborhoodScores(
        name="Hjorthagen",
        safety=8,
        green_space=7,
        amenities=6,  # Developing area
        restaurants=5,
        family_friendly=8,
        expat_friendly=6,
    ),
    # === Western areas ===
    "liljeholmen": NeighborhoodScores(
        name="Liljeholmen",
        safety=8,
        green_space=6,
        amenities=8,  # Liljeholmstorget mall
        restaurants=6,
        family_friendly=7,
        expat_friendly=6,
    ),
    "hornstull": NeighborhoodScores(
        name="Hornstull",
        safety=8,
        green_space=6,  # Tantolunden
        amenities=8,
        restaurants=8,  # Popular area
        family_friendly=6,
        expat_friendly=8,
    ),
    "fridhemsplan": NeighborhoodScores(
        name="Fridhemsplan",
        safety=9,
        green_space=7,
        amenities=8,
        restaurants=7,
        family_friendly=8,
        expat_friendly=8,
    ),
    # === Vasastan sub-areas ===
    "odenplan": NeighborhoodScores(
        name="Odenplan",
        safety=9,
        green_space=5,  # Vasaparken nearby
        amenities=8,
        restaurants=8,
        family_friendly=7,
        expat_friendly=8,
    ),
    "sankt eriksplan": NeighborhoodScores(
        name="Sankt Eriksplan",
        safety=9,
        green_space=6,
        amenities=7,
        restaurants=7,
        family_friendly=8,
        expat_friendly=7,
    ),
    # === Nearby municipalities ===
    "solna": NeighborhoodScores(
        name="Solna",
        safety=8,
        green_space=8,  # Hagaparken, Ulriksdal
        amenities=8,  # Mall of Scandinavia
        restaurants=6,
        family_friendly=8,
        expat_friendly=7,
    ),
    "sundbyberg": NeighborhoodScores(
        name="Sundbyberg",
        safety=8,
        green_space=6,
        amenities=7,
        restaurants=6,
        family_friendly=7,
        expat_friendly=6,
    ),
    "nacka": NeighborhoodScores(
        name="Nacka",
        safety=9,
        green_space=9,  # Nature reserves
        amenities=7,
        restaurants=5,
        family_friendly=9,
        expat_friendly=6,
    ),
    "lidingö": NeighborhoodScores(
        name="Lidingö",
        safety=9,
        green_space=9,  # Island, very green
        amenities=6,
        restaurants=5,
        family_friendly=9,
        expat_friendly=6,
    ),
    "danderyd": NeighborhoodScores(
        name="Danderyd",
        safety=9,
        green_space=8,
        amenities=6,
        restaurants=5,
        family_friendly=9,
        expat_friendly=7,  # Affluent area
    ),
    "bromma": NeighborhoodScores(
        name="Bromma",
        safety=9,
        green_space=8,
        amenities=7,
        restaurants=5,
        family_friendly=9,
        expat_friendly=7,
    ),
    "huddinge": NeighborhoodScores(
        name="Huddinge",
        safety=7,
        green_space=8,
        amenities=6,
        restaurants=5,
        family_friendly=8,
        expat_friendly=5,
    ),
    "täby": NeighborhoodScores(
        name="Täby",
        safety=9,
        green_space=8,
        amenities=8,  # Täby Centrum
        restaurants=6,
        family_friendly=9,
        expat_friendly=6,
    ),
    "sollentuna": NeighborhoodScores(
        name="Sollentuna",
        safety=8,
        green_space=8,
        amenities=7,
        restaurants=5,
        family_friendly=8,
        expat_friendly=5,
    ),
    "järfälla": NeighborhoodScores(
        name="Järfälla",
        safety=7,
        green_space=8,
        amenities=6,
        restaurants=4,
        family_friendly=7,
        expat_friendly=4,
    ),
}

# City-specific neighborhood data lookup
CITY_NEIGHBORHOOD_DATA: dict[str, dict[str, NeighborhoodScores]] = {
    "amsterdam": NEIGHBORHOOD_DATA,
    "helsinki": HELSINKI_NEIGHBORHOOD_DATA,
    "stockholm": STOCKHOLM_NEIGHBORHOOD_DATA,
}

# Alternative name mappings for neighborhood detection (Amsterdam)
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

# Alternative name mappings for Helsinki neighborhood detection
HELSINKI_NEIGHBORHOOD_ALIASES: dict[str, str] = {
    # Finnish/Swedish variations
    "tölö": "töölö",
    "berghäll": "kallio",  # Swedish name
    "drumsö": "lauttasaari",  # Swedish name
    "busholmen": "jätkäsaari",  # Swedish name
    "gräsviken": "ruoholahti",  # Swedish name
    "hagalund": "tapiola",  # Swedish name
    "otnäs": "otaniemi",  # Swedish name
    "alberga": "leppävaara",  # Swedish name
    "mattby": "matinkylä",  # Swedish name
    # Area variations
    "espoo centre": "espoo center",
    "espoon keskus": "espoo center",
    "sello": "leppävaara",
    "iso omena": "matinkylä",
    "aalto university": "otaniemi",
    "aalto": "otaniemi",
    "design district": "punavuori",
    "eira": "ullanlinna",
    "kaivopuisto": "ullanlinna",
}

# Alternative name mappings for Stockholm neighborhood detection
STOCKHOLM_NEIGHBORHOOD_ALIASES: dict[str, str] = {
    # Common variations
    "city": "norrmalm",
    "t-centralen": "norrmalm",
    "sergels torg": "norrmalm",
    "stureplan": "östermalm",
    "karlaplan": "östermalm",
    "söder": "södermalm",
    "medborgarplatsen": "södermalm",
    "slussen": "södermalm",
    "mariatorget": "södermalm",
    "vasa": "vasastan",
    "sveavägen": "vasastan",
    "st eriksplan": "sankt eriksplan",
    "fridhem": "fridhemsplan",
    "kungsholms torg": "kungsholmen",
    "kungsan": "kungsholmen",
    "gamla staden": "gamla stan",
    "old town": "gamla stan",
    "djurgård": "djurgården",
    "hammarby": "hammarby sjöstad",
    "sjöstaden": "hammarby sjöstad",
    "lilla essingen": "kungsholmen",
    "stora essingen": "kungsholmen",
    "reimersholme": "södermalm",
    "långholmen": "södermalm",
    "skeppsholmen": "gamla stan",
    # Municipality variations
    "solna centrum": "solna",
    "solna stad": "solna",
    "hagalund": "solna",
    "bergshamra": "solna",
    "mall of scandinavia": "solna",
    "arenastaden": "solna",
    "sundbybergs stad": "sundbyberg",
    "nacka strand": "nacka",
    "nacka forum": "nacka",
    "sickla": "nacka",
    "saltsjöbaden": "nacka",
    "lidingö stad": "lidingö",
    "danderyd centrum": "danderyd",
    "djursholm": "danderyd",
    "stocksund": "danderyd",
    "täby centrum": "täby",
    "arninge": "täby",
    "sollentuna centrum": "sollentuna",
    "tureberg": "sollentuna",
    "jakobsberg": "järfälla",
    "barkarby": "järfälla",
    "flemingsberg": "huddinge",
    "huddinge centrum": "huddinge",
    "bromma centrum": "bromma",
    "brommaplan": "bromma",
    "alvik": "bromma",
    "traneberg": "bromma",
    "mariehäll": "bromma",
    "äppelviken": "bromma",
}

# City-specific aliases
CITY_NEIGHBORHOOD_ALIASES: dict[str, dict[str, str]] = {
    "amsterdam": NEIGHBORHOOD_ALIASES,
    "helsinki": HELSINKI_NEIGHBORHOOD_ALIASES,
    "stockholm": STOCKHOLM_NEIGHBORHOOD_ALIASES,
}


def normalize_neighborhood_name(name: str, target_city: str = "amsterdam") -> str:
    """Normalize a neighborhood name for lookup."""
    if not name:
        return ""
    # Lowercase and strip
    normalized = name.lower().strip()
    # Remove common prefixes based on city
    if target_city == "amsterdam":
        for prefix in ["amsterdam ", "amsterdam-"]:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
    elif target_city == "helsinki":
        for prefix in ["helsinki ", "helsinki-", "espoo ", "espoo-"]:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
    elif target_city == "stockholm":
        for prefix in ["stockholm ", "stockholm-", "stockholms "]:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
    return normalized


def identify_neighborhood_amsterdam(
    address: str = None,
    city_field: str = None,
    neighborhood: str = None,
    postal_code: str = None,
) -> Optional[str]:
    """
    Identify the Amsterdam neighborhood from address components.

    Returns the normalized neighborhood key or None if not identified.
    """
    # Check for non-Amsterdam municipalities first (by city name)
    if city_field:
        city_lower = city_field.lower().strip()
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
    if city_field:
        search_parts.append(city_field.lower())
    if address:
        # Handle address as dict (from geocoding) or string
        if isinstance(address, dict):
            # Extract string parts from the address dict
            addr_parts = [str(v) for v in address.values() if v]
            search_parts.append(" ".join(addr_parts).lower())
        else:
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


def identify_neighborhood_helsinki(
    address: str = None,
    city_field: str = None,
    neighborhood: str = None,
    postal_code: str = None,
) -> Optional[str]:
    """
    Identify the Helsinki/Espoo neighborhood from address components.

    Returns the normalized neighborhood key or None if not identified.
    """
    # Build search text from all available fields
    search_parts = []
    if neighborhood:
        search_parts.append(neighborhood.lower())
    if city_field:
        search_parts.append(city_field.lower())
    if address:
        # Handle address as dict (from geocoding) or string
        if isinstance(address, dict):
            addr_parts = [str(v) for v in address.values() if v]
            search_parts.append(" ".join(addr_parts).lower())
        else:
            search_parts.append(address.lower())

    search_text = " ".join(search_parts)

    # Try direct match in Helsinki aliases first
    for alias, key in HELSINKI_NEIGHBORHOOD_ALIASES.items():
        if alias in search_text:
            return key

    # Try direct neighborhood name match
    for key in HELSINKI_NEIGHBORHOOD_DATA.keys():
        # Check if the neighborhood name appears in the text
        if key in search_text or key.replace("-", " ") in search_text:
            return key

    # Try Finnish postal code heuristic
    # Helsinki: 00100-00990
    # Espoo: 02100-02980
    if postal_code:
        postal_clean = postal_code.replace(" ", "").upper()
        postal_match = re.match(r"(\d{5})", postal_clean)
        if postal_match:
            postal_num = int(postal_match.group(1))

            # Helsinki central (00100-00180)
            if 100 <= postal_num <= 120:
                return "kamppi"
            elif 121 <= postal_num <= 140:
                return "punavuori"
            elif 141 <= postal_num <= 160:
                return "ullanlinna"
            elif 161 <= postal_num <= 180:
                return "kruununhaka"

            # Töölö area (00250-00270)
            elif 250 <= postal_num <= 270:
                return "töölö"

            # Kallio area (00500-00560)
            elif 500 <= postal_num <= 560:
                return "kallio"

            # Pasila area (00520-00540)
            elif 520 <= postal_num <= 540:
                return "pasila"

            # Sörnäinen/Vallila (00510, 00550)
            elif 510 <= postal_num <= 515:
                return "sörnäinen"
            elif 550 <= postal_num <= 560:
                return "vallila"

            # Eastern Helsinki
            elif 570 <= postal_num <= 590:
                return "arabia"
            elif 800 <= postal_num <= 830:
                return "herttoniemi"
            elif 840 <= postal_num <= 850:
                return "kulosaari"
            elif 900 <= postal_num <= 990:
                return "vuosaari"
            elif 940 <= postal_num <= 970:
                return "kontula"

            # Northern Helsinki
            elif 600 <= postal_num <= 650:
                return "käpylä"
            elif 660 <= postal_num <= 690:
                return "oulunkylä"
            elif 700 <= postal_num <= 770:
                return "malmi"

            # Western Helsinki
            elif 330 <= postal_num <= 350:
                return "munkkiniemi"
            elif 200 <= postal_num <= 220:
                return "lauttasaari"
            elif 180 <= postal_num <= 185:
                return "jätkäsaari"
            elif 186 <= postal_num <= 190:
                return "ruoholahti"

            # Espoo (02xxx)
            elif 2100 <= postal_num <= 2140:
                return "tapiola"
            elif 2150 <= postal_num <= 2159:
                return "otaniemi"
            elif 2160 <= postal_num <= 2175:
                return "keilaniemi"
            elif 2600 <= postal_num <= 2650:
                return "espoo center"
            elif 2200 <= postal_num <= 2250:
                return "matinkylä"
            elif 2320 <= postal_num <= 2380:
                return "leppävaara"

    return None


def identify_neighborhood_stockholm(
    address: str = None,
    city_field: str = None,
    neighborhood: str = None,
    postal_code: str = None,
) -> Optional[str]:
    """
    Identify the Stockholm neighborhood from address components.

    Returns the normalized neighborhood key or None if not identified.
    """
    # Check for non-Stockholm municipalities first (by city name)
    if city_field:
        city_lower = city_field.lower().strip()
        # Direct municipality matches
        non_stockholm_cities = [
            "solna", "sundbyberg", "nacka", "lidingö", "danderyd",
            "bromma", "huddinge", "täby", "sollentuna", "järfälla"
        ]
        for muni in non_stockholm_cities:
            if muni in city_lower or city_lower == muni:
                if muni in STOCKHOLM_NEIGHBORHOOD_DATA:
                    return muni

    # Build search text from all available fields
    search_parts = []
    if neighborhood:
        search_parts.append(neighborhood.lower())
    if city_field:
        search_parts.append(city_field.lower())
    if address:
        # Handle address as dict (from geocoding) or string
        if isinstance(address, dict):
            addr_parts = [str(v) for v in address.values() if v]
            search_parts.append(" ".join(addr_parts).lower())
        else:
            search_parts.append(address.lower())

    search_text = " ".join(search_parts)

    # Try direct match in Stockholm aliases first
    for alias, key in STOCKHOLM_NEIGHBORHOOD_ALIASES.items():
        if alias in search_text:
            return key

    # Try direct neighborhood name match
    for key in STOCKHOLM_NEIGHBORHOOD_DATA.keys():
        # Skip municipality names (already checked above)
        if key in ["solna", "sundbyberg", "nacka", "lidingö", "danderyd",
                   "bromma", "huddinge", "täby", "sollentuna", "järfälla"]:
            continue
        # Check if the neighborhood name appears in the text
        if key in search_text or key.replace("-", " ") in search_text:
            return key

    # Try Swedish postal code heuristic
    # Stockholm inner city: 100xx-118xx
    # Suburbs and municipalities vary
    if postal_code:
        postal_clean = postal_code.replace(" ", "").upper()
        postal_match = re.match(r"(\d{3})\s*(\d{2})", postal_clean)
        if postal_match:
            postal_prefix = int(postal_match.group(1))

            # Stockholm city postal codes (1xx xx)
            if 100 <= postal_prefix <= 104:
                return "norrmalm"
            elif 105 <= postal_prefix <= 107:
                return "södermalm"
            elif 108 <= postal_prefix <= 112:
                return "södermalm"
            elif 113 <= postal_prefix <= 114:
                return "östermalm"
            elif 115 <= postal_prefix <= 116:
                return "östermalm"
            elif 117 <= postal_prefix <= 118:
                return "södermalm"
            elif 111 <= postal_prefix <= 112:
                return "gamla stan"
            # Vasastan area (113xx, parts)
            elif postal_prefix == 113:
                return "vasastan"
            # Kungsholmen (112xx)
            elif postal_prefix == 112:
                return "kungsholmen"
            # Gärdet/Djurgården (115xx)
            elif postal_prefix == 115:
                return "gärdet"
            # Hammarby Sjöstad (120xx-121xx)
            elif 120 <= postal_prefix <= 121:
                return "hammarby sjöstad"
            # Liljeholmen (117xx)
            elif postal_prefix == 117:
                return "liljeholmen"
            # Bromma (162xx-168xx)
            elif 162 <= postal_prefix <= 168:
                return "bromma"
            # Solna (169xx-171xx)
            elif 169 <= postal_prefix <= 171:
                return "solna"
            # Sundbyberg (172xx-174xx)
            elif 172 <= postal_prefix <= 174:
                return "sundbyberg"
            # Nacka (131xx-133xx)
            elif 131 <= postal_prefix <= 133:
                return "nacka"
            # Lidingö (181xx-185xx)
            elif 181 <= postal_prefix <= 185:
                return "lidingö"
            # Danderyd (182xx-183xx)
            elif 182 <= postal_prefix <= 183:
                return "danderyd"
            # Täby (183xx-187xx)
            elif 183 <= postal_prefix <= 187:
                return "täby"
            # Sollentuna (191xx-192xx)
            elif 191 <= postal_prefix <= 192:
                return "sollentuna"
            # Järfälla (175xx-177xx)
            elif 175 <= postal_prefix <= 177:
                return "järfälla"
            # Huddinge (141xx-143xx)
            elif 141 <= postal_prefix <= 143:
                return "huddinge"

    return None


def identify_neighborhood(
    address: str = None,
    city_field: str = None,
    neighborhood: str = None,
    postal_code: str = None,
    target_city: str = "amsterdam",
) -> Optional[str]:
    """
    Identify the neighborhood from address components.

    Args:
        address: Street address
        city_field: City name from listing
        neighborhood: Neighborhood name from listing
        postal_code: Postal code
        target_city: Which city's neighborhoods to search (amsterdam, helsinki)

    Returns the normalized neighborhood key or None if not identified.
    """
    target_city = (target_city or "amsterdam").lower()

    if target_city == "helsinki":
        return identify_neighborhood_helsinki(address, city_field, neighborhood, postal_code)
    elif target_city == "stockholm":
        return identify_neighborhood_stockholm(address, city_field, neighborhood, postal_code)
    else:
        return identify_neighborhood_amsterdam(address, city_field, neighborhood, postal_code)


def get_neighborhood_scores(
    address: str = None,
    city_field: str = None,
    neighborhood: str = None,
    postal_code: str = None,
    target_city: str = "amsterdam",
) -> Optional[NeighborhoodScores]:
    """
    Get neighborhood scores for a location.

    Args:
        address: Street address
        city_field: City name from listing
        neighborhood: Neighborhood name from listing
        postal_code: Postal code
        target_city: Which city's neighborhoods to search (amsterdam, helsinki)

    Returns NeighborhoodScores if the neighborhood can be identified, None otherwise.
    """
    target_city = (target_city or "amsterdam").lower()
    key = identify_neighborhood(address, city_field, neighborhood, postal_code, target_city)

    if key:
        neighborhood_data = CITY_NEIGHBORHOOD_DATA.get(target_city, NEIGHBORHOOD_DATA)
        if key in neighborhood_data:
            return neighborhood_data[key]
    return None


def enrich_listing_with_neighborhood(listing: dict, city: str = None) -> dict:
    """
    Add neighborhood quality scores to a listing.

    Args:
        listing: The listing dict to enrich
        city: Target city for neighborhood lookup (amsterdam, helsinki)

    Modifies the listing dict in place and returns it.
    """
    target_city = (city or "amsterdam").lower()

    scores = get_neighborhood_scores(
        address=listing.get("address"),
        city_field=listing.get("city"),
        neighborhood=listing.get("neighborhood"),
        postal_code=listing.get("postal_code"),
        target_city=target_city,
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
