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
    """Try to extract JSON from LLM response."""
    # Try direct parse first
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to find JSON block in response
    json_match = re.search(r"\{[\s\S]*\}", response)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

    # Try to fix common issues
    cleaned = response.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    try:
        return json.loads(cleaned.strip())
    except json.JSONDecodeError:
        return None


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

    def extract_from_html(self, html: str, raw_data: dict = None) -> dict:
        """Extract structured fields from HTML content using LLM."""
        text = extract_text_from_html(html)

        prompt = EXTRACTION_PROMPT.format(content=text)

        try:
            response = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.1, "num_predict": 2000},
            )

            llm_data = extract_json_from_response(response.response)

            if llm_data:
                # Merge with raw_data, preferring raw_data for existing fields
                if raw_data:
                    for key, value in llm_data.items():
                        if key not in raw_data or raw_data.get(key) is None:
                            raw_data[key] = value
                    return raw_data
                return llm_data
            else:
                console.print("[yellow]Could not parse LLM response as JSON[/]")
                return raw_data or {}

        except Exception as e:
            console.print(f"[red]LLM extraction failed: {e}[/]")
            return raw_data or {}

    def enrich_listing(self, listing_data: dict, raw_html_path: str = None) -> dict:
        """Enrich a listing with LLM-extracted data."""
        if raw_html_path:
            try:
                with open(raw_html_path, "r", encoding="utf-8") as f:
                    html = f.read()
                return self.extract_from_html(html, listing_data)
            except Exception as e:
                console.print(f"[red]Could not read HTML file: {e}[/]")

        return listing_data
