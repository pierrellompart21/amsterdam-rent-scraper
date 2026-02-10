"""LLM-based extraction using Ollama for structured data extraction from rental listings."""

import json
import re
from typing import Optional

import ollama
from rich.console import Console

from amsterdam_rent_scraper.config.settings import (
    LLM_MAX_INPUT_CHARS,
    LLM_TIMEOUT,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)
from amsterdam_rent_scraper.llm.regex_fallback import regex_extract_from_html

console = Console()

EXTRACTION_PROMPT = """You are extracting structured rental listing information from a Dutch housing website page.

Extract the following fields from the content. Return ONLY valid JSON with these exact keys (use null for missing values):

{{
  "title": "listing title or address",
  "price_eur": 1500,
  "address": "full street address",
  "city": "city name",
  "neighborhood": "neighborhood or district",
  "postal_code": "1234AB",
  "surface_m2": 75,
  "rooms": 3,
  "bedrooms": 2,
  "bathrooms": 1,
  "floor": "2nd floor",
  "furnished": "Furnished/Unfurnished/Upholstered",
  "property_type": "Apartment/Studio/House",
  "deposit_eur": 1500,
  "available_date": "2024-03-01 or Immediately",
  "minimum_contract_months": 12,
  "pets_allowed": "Yes/No/Unknown",
  "smoking_allowed": "Yes/No/Unknown",
  "energy_label": "A/B/C/D/E/F/G",
  "building_year": 1990,
  "landlord_name": "name if shown",
  "agency": "real estate agency name",
  "description_summary": "2-3 sentence summary of the listing",
  "pros": "key positive aspects (location, amenities, etc)",
  "cons": "any red flags or downsides mentioned",
  "neighborhood_score": "Good/Average/Below Average based on description"
}}

Important:
- Extract numbers as integers or floats, not strings
- Use null for any field you cannot find
- For price, extract the monthly rent amount only
- For surface_m2, extract the number only
- Summarize the description in 2-3 sentences
- Identify pros/cons based on the listing description

PAGE CONTENT:
{content}

Respond with ONLY the JSON object, no explanation or markdown."""


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML, removing scripts and styles."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    # Remove script and style elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    # Get text
    text = soup.get_text(separator="\n", strip=True)

    # Clean up whitespace
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    # Truncate to fit LLM context
    return text[:LLM_MAX_INPUT_CHARS]


def extract_json_from_response(response: str) -> Optional[dict]:
    """Try to extract JSON from LLM response with robust parsing."""
    if not response or not response.strip():
        return None

    # Try direct parse first
    try:
        result = json.loads(response)
        return _normalize_llm_fields(result)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in response (greedy match for outermost braces)
    # Handle nested objects properly by finding balanced braces
    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        try:
            result = json.loads(json_match.group())
            return _normalize_llm_fields(result)
        except json.JSONDecodeError:
            pass

    # Try to fix common issues
    cleaned = response.strip()

    # Remove markdown code blocks
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    # Fix common JSON issues
    # 1. Remove trailing commas before closing braces
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    # 2. Fix single quotes to double quotes (common LLM mistake)
    # Only do this if the string doesn't parse as-is
    try:
        result = json.loads(cleaned)
        return _normalize_llm_fields(result)
    except json.JSONDecodeError:
        pass

    # Try single-to-double quote conversion (risky, but last resort)
    try:
        # Only convert quotes that look like JSON delimiters
        cleaned_quotes = re.sub(r"'([^']*)'(\s*:)", r'"\1"\2', cleaned)
        cleaned_quotes = re.sub(r":\s*'([^']*)'(\s*[,}\]])", r': "\1"\2', cleaned_quotes)
        result = json.loads(cleaned_quotes)
        return _normalize_llm_fields(result)
    except json.JSONDecodeError:
        return None


def _normalize_llm_fields(data: dict) -> dict:
    """Normalize LLM-extracted fields to expected types.

    Ensures fields like pros, cons, description_summary are strings, not lists.
    """
    if not isinstance(data, dict):
        return data

    # Fields that should be strings but LLM might return as lists
    string_fields = {
        "pros", "cons", "description_summary", "title", "address",
        "neighborhood", "floor", "furnished", "property_type",
        "pets_allowed", "smoking_allowed", "energy_label",
        "landlord_name", "agency", "available_date", "neighborhood_score"
    }

    for field in string_fields:
        value = data.get(field)
        if isinstance(value, list):
            # Convert list to comma-separated string
            data[field] = ", ".join(str(item) for item in value if item)
        elif isinstance(value, dict):
            # Convert dict to string representation
            data[field] = str(value)

    # Ensure numeric fields are numbers
    numeric_fields = {
        "price_eur": float,
        "surface_m2": float,
        "rooms": int,
        "bedrooms": int,
        "bathrooms": int,
        "deposit_eur": float,
        "minimum_contract_months": int,
        "building_year": int,
    }

    for field, expected_type in numeric_fields.items():
        value = data.get(field)
        if value is not None and not isinstance(value, (int, float)):
            try:
                # Try to extract number from string
                if isinstance(value, str):
                    # Remove currency symbols, spaces, etc.
                    clean_value = re.sub(r"[^\d.,]", "", value)
                    if clean_value:
                        # Handle different number formats:
                        # - "1,500" or "1.500" (thousands separator) -> 1500
                        # - "1,5" or "1.5" (decimal) -> 1.5
                        # - "1,500.50" (US format) -> 1500.50
                        # - "1.500,50" (EU format) -> 1500.50

                        if "," in clean_value and "." in clean_value:
                            # Both present: determine which is decimal separator
                            last_comma = clean_value.rfind(",")
                            last_dot = clean_value.rfind(".")
                            if last_comma > last_dot:
                                # EU format: 1.500,50
                                clean_value = clean_value.replace(".", "").replace(",", ".")
                            else:
                                # US format: 1,500.50
                                clean_value = clean_value.replace(",", "")
                        elif "," in clean_value:
                            # Only comma - check if it's decimal or thousands
                            parts = clean_value.split(",")
                            if len(parts) == 2 and len(parts[1]) <= 2:
                                # Likely decimal (e.g., "1,5" or "1,50")
                                clean_value = clean_value.replace(",", ".")
                            else:
                                # Likely thousands separator (e.g., "1,500")
                                clean_value = clean_value.replace(",", "")
                        elif "." in clean_value:
                            # Only dot - check if it's decimal or thousands
                            parts = clean_value.split(".")
                            if len(parts) == 2 and len(parts[1]) <= 2:
                                # Likely decimal (e.g., "1.5" or "1.50")
                                pass  # Keep as is
                            elif len(parts) == 2 and len(parts[1]) == 3:
                                # Likely thousands separator (e.g., "1.500")
                                clean_value = clean_value.replace(".", "")

                        data[field] = expected_type(float(clean_value))
            except (ValueError, TypeError):
                data[field] = None

    return data


class OllamaExtractor:
    """Extract structured data from rental listings using Ollama LLM."""

    def __init__(self, model: str = None, base_url: str = None):
        self.model = model or OLLAMA_MODEL
        self.base_url = base_url or OLLAMA_BASE_URL
        self.client = ollama.Client(host=self.base_url)

    def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            models = self.client.list()
            model_names = [m.model for m in models.models]
            # Check if our model (or a variant) is available
            for name in model_names:
                if self.model in name or name.startswith(self.model):
                    return True
            console.print(
                f"[yellow]Model {self.model} not found. Available: {model_names}[/]"
            )
            return False
        except Exception as e:
            console.print(f"[red]Ollama not available: {e}[/]")
            return False

    def extract_from_html(self, html: str, raw_data: dict = None) -> tuple[dict, bool]:
        """Extract structured fields from HTML content using LLM with regex fallback.

        Returns:
            Tuple of (result_dict, llm_success) where llm_success indicates if LLM parsing worked.
        """
        text = extract_text_from_html(html)

        prompt = EXTRACTION_PROMPT.format(content=text)

        result = raw_data.copy() if raw_data else {}
        llm_success = False

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.1, "num_predict": 2000},
            )

            llm_data = extract_json_from_response(response.response)

            if llm_data:
                # Merge LLM data, preferring existing raw_data fields
                for key, value in llm_data.items():
                    if key not in result or result.get(key) is None:
                        result[key] = value
                llm_success = True
            else:
                console.print("[yellow]Could not parse LLM response as JSON[/]")

        except Exception as e:
            console.print(f"[red]LLM extraction failed: {e}[/]")

        # Apply regex fallback to fill in any remaining missing fields
        result = regex_extract_from_html(html, result)

        return result, llm_success

    def enrich_listing(self, listing_data: dict, raw_html_path: str = None) -> tuple[dict, bool]:
        """Enrich a listing with LLM-extracted data.

        Returns:
            Tuple of (enriched_dict, llm_success) where llm_success indicates if LLM parsing worked.
        """
        if raw_html_path:
            try:
                with open(raw_html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                return self.extract_from_html(html, listing_data)
            except Exception as e:
                console.print(f"[red]Could not read HTML file: {e}[/]")

        return listing_data, False
