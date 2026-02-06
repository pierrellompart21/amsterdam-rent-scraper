"""Regex-based fallback extraction for when LLM output is incomplete."""

import re
from typing import Optional

from bs4 import BeautifulSoup


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def extract_price(text: str) -> Optional[float]:
    """Extract monthly rent price in EUR."""
    # Patterns for Dutch rental prices
    patterns = [
        # "€ 1.500" or "€1500" or "EUR 1500"
        r"(?:€|EUR|eur)\s*(\d{1,2}[\.,]\d{3}|\d{3,4})(?:\s*(?:per|/|p/m|p\.m\.|pm|per maand|p/mnd))?",
        # "1.500 euro" or "1500 EUR"
        r"(\d{1,2}[\.,]\d{3}|\d{3,4})\s*(?:€|EUR|euro)",
        # "Huur: 1500" or "Huurprijs: € 1.500"
        r"(?:huur(?:prijs)?|rent|price)[:\s]*(?:€|EUR)?\s*(\d{1,2}[\.,]\d{3}|\d{3,4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            price_str = match.group(1)
            # Convert "1.500" or "1,500" to 1500
            price_str = price_str.replace(".", "").replace(",", "")
            try:
                price = float(price_str)
                # Filter out unrealistic prices (likely not monthly rent)
                if 300 <= price <= 10000:
                    return price
            except ValueError:
                continue
    return None


def extract_surface(text: str) -> Optional[float]:
    """Extract surface area in m2."""
    patterns = [
        # "75 m²" or "75m2" or "75 m2"
        r"(\d{2,4})\s*(?:m²|m2|vierkante meter|sqm)",
        # "Oppervlakte: 75" or "Woonoppervlakte: 75 m²"
        r"(?:opp(?:ervlakte)?|woon(?:oppervlakte)?|living\s*area|surface)[:\s]*(\d{2,4})\s*(?:m²|m2)?",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                surface = float(match.group(1))
                # Filter out unrealistic values
                if 10 <= surface <= 1000:
                    return surface
            except ValueError:
                continue
    return None


def extract_rooms(text: str) -> Optional[int]:
    """Extract number of rooms."""
    patterns = [
        # "3 kamers" or "3-kamer"
        r"(\d)\s*(?:-?\s*)?kamers?(?:\s*woning)?",
        # "3 rooms"
        r"(\d)\s*rooms?",
        # "Kamers: 3"
        r"(?:kamers?|rooms?)[:\s]*(\d)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                rooms = int(match.group(1))
                if 1 <= rooms <= 20:
                    return rooms
            except ValueError:
                continue
    return None


def extract_bedrooms(text: str) -> Optional[int]:
    """Extract number of bedrooms."""
    patterns = [
        # "2 slaapkamers"
        r"(\d)\s*slaapkamers?",
        # "2 bedrooms"
        r"(\d)\s*bedrooms?",
        # "Slaapkamers: 2"
        r"(?:slaapkamers?|bedrooms?)[:\s]*(\d)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return None


def extract_postal_code(text: str) -> Optional[str]:
    """Extract Dutch postal code (1234 AB format)."""
    # Dutch postal code: 4 digits + 2 letters
    match = re.search(r"\b(\d{4}\s*[A-Za-z]{2})\b", text)
    if match:
        pc = match.group(1).upper()
        # Normalize spacing
        if len(pc) == 6:
            pc = pc[:4] + " " + pc[4:]
        return pc
    return None


def extract_floor(text: str) -> Optional[str]:
    """Extract floor information."""
    patterns = [
        # "2e verdieping" or "tweede verdieping"
        r"(\d+)e?\s*verdieping",
        # "2nd floor" or "second floor"
        r"(\d+)(?:st|nd|rd|th)\s*floor",
        # "Etage: 2" or "Verdieping: 2"
        r"(?:etage|verdieping|floor)[:\s]*(\d+)",
        # "begane grond" = ground floor
        r"(begane\s*grond|ground\s*floor)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            floor = match.group(1)
            if floor.lower() in ["begane grond", "ground floor"]:
                return "Ground floor"
            return f"Floor {floor}"
    return None


def extract_energy_label(text: str) -> Optional[str]:
    """Extract energy label (A-G)."""
    patterns = [
        # "Energielabel: A" or "Energy label A"
        r"(?:energie\s*label|energy\s*label)[:\s]*([A-Ga-g](?:\+{1,3})?)",
        # Just "Label A" or "Label: B"
        r"\blabel[:\s]*([A-Ga-g](?:\+{1,3})?)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
    return None


def extract_deposit(text: str) -> Optional[float]:
    """Extract deposit amount in EUR."""
    patterns = [
        # "Borg: € 1.500" or "Deposit: 1500"
        r"(?:borg|deposit|waarborgsom)[:\s]*(?:€|EUR)?\s*(\d{1,2}[\.,]\d{3}|\d{3,4})",
        # "€ 1.500 borg"
        r"(?:€|EUR)\s*(\d{1,2}[\.,]\d{3}|\d{3,4})\s*(?:borg|deposit)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            deposit_str = match.group(1)
            deposit_str = deposit_str.replace(".", "").replace(",", "")
            try:
                deposit = float(deposit_str)
                if 100 <= deposit <= 20000:
                    return deposit
            except ValueError:
                continue
    return None


def extract_furnished(text: str) -> Optional[str]:
    """Extract furnished status."""
    text_lower = text.lower()

    # Check for unfurnished first (more specific)
    if any(word in text_lower for word in ["unfurnished", "ongemeubileerd", "kaal"]):
        return "Unfurnished"

    # Check for upholstered/semi-furnished
    if any(word in text_lower for word in ["upholstered", "gestoffeerd"]):
        return "Upholstered"

    # Check for furnished
    if any(word in text_lower for word in ["furnished", "gemeubileerd"]):
        return "Furnished"

    return None


def extract_available_date(text: str) -> Optional[str]:
    """Extract availability date."""
    text_lower = text.lower()

    # Immediate availability
    if any(phrase in text_lower for phrase in ["per direct", "immediately", "direct beschikbaar", "nu beschikbaar"]):
        return "Immediately"

    patterns = [
        # "Beschikbaar: 01-03-2024" or "Available from: 2024-03-01"
        r"(?:beschikbaar|available|per)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
        r"(?:beschikbaar|available|per)[:\s]*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
        # Just a date pattern near availability keywords
        r"(?:from|vanaf|per)\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_building_year(text: str) -> Optional[int]:
    """Extract year of construction."""
    patterns = [
        # "Bouwjaar: 1990" or "Built in 1990"
        r"(?:bouwjaar|built|construction|year)[:\s]*(\d{4})",
        # "uit 1990" (from 1990)
        r"uit\s+(\d{4})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                year = int(match.group(1))
                if 1800 <= year <= 2030:
                    return year
            except ValueError:
                continue
    return None


def extract_property_type(text: str) -> Optional[str]:
    """Extract property type."""
    text_lower = text.lower()

    type_mapping = {
        "studio": ["studio"],
        "apartment": ["appartement", "apartment", "flat"],
        "house": ["woning", "huis", "house", "eengezinswoning"],
        "room": ["kamer", "room"],
    }

    for prop_type, keywords in type_mapping.items():
        if any(keyword in text_lower for keyword in keywords):
            return prop_type.capitalize()
    return None


def regex_extract_from_html(html: str, existing_data: dict = None) -> dict:
    """
    Extract rental listing data using regex patterns.

    This serves as a fallback when LLM extraction is incomplete or unavailable.
    Only fills in fields that are missing from existing_data.
    """
    text = extract_text_from_html(html)
    existing_data = existing_data or {}

    # Map of field names to extraction functions
    extractors = {
        "price_eur": extract_price,
        "surface_m2": extract_surface,
        "rooms": extract_rooms,
        "bedrooms": extract_bedrooms,
        "postal_code": extract_postal_code,
        "floor": extract_floor,
        "energy_label": extract_energy_label,
        "deposit_eur": extract_deposit,
        "furnished": extract_furnished,
        "available_date": extract_available_date,
        "building_year": extract_building_year,
        "property_type": extract_property_type,
    }

    result = dict(existing_data)

    for field, extractor in extractors.items():
        # Only extract if field is missing or None
        if result.get(field) is None:
            extracted = extractor(text)
            if extracted is not None:
                result[field] = extracted

    return result
