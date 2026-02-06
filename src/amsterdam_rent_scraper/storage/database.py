"""SQLite database for storing rental listings with deduplication."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from amsterdam_rent_scraper.models.listing import RentalListing


class ListingDatabase:
    """SQLite database for storing and retrieving rental listings."""

    # Columns in the database schema
    DB_COLUMNS = {
        "listing_url", "source_site", "raw_page_path", "scraped_at", "last_seen_at",
        "title", "price_eur", "address", "city", "neighborhood", "postal_code",
        "latitude", "longitude", "surface_m2", "rooms", "bedrooms", "bathrooms",
        "floor", "furnished", "property_type", "deposit_eur", "available_date",
        "minimum_contract_months", "pets_allowed", "smoking_allowed", "energy_label",
        "building_year", "landlord_name", "landlord_phone", "agency",
        "description_summary", "pros", "cons", "distance_km", "commute_time_bike_min",
        "commute_time_transit_min", "commute_time_driving_min", "transit_transfers",
        "bike_route_coords", "neighborhood_name", "neighborhood_safety",
        "neighborhood_green_space", "neighborhood_amenities", "neighborhood_restaurants",
        "neighborhood_family_friendly", "neighborhood_expat_friendly", "neighborhood_overall"
    }

    def __init__(self, db_path: Path | str = "listings.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_url TEXT UNIQUE NOT NULL,
                source_site TEXT NOT NULL,
                raw_page_path TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Core details
                title TEXT,
                price_eur REAL,
                address TEXT,
                city TEXT,
                neighborhood TEXT,
                postal_code TEXT,
                latitude REAL,
                longitude REAL,

                -- Property details
                surface_m2 REAL,
                rooms INTEGER,
                bedrooms INTEGER,
                bathrooms INTEGER,
                floor TEXT,
                furnished TEXT,
                property_type TEXT,

                -- Conditions
                deposit_eur REAL,
                available_date TEXT,
                minimum_contract_months INTEGER,
                pets_allowed TEXT,
                smoking_allowed TEXT,
                energy_label TEXT,
                building_year INTEGER,

                -- Landlord
                landlord_name TEXT,
                landlord_phone TEXT,
                agency TEXT,

                -- LLM analysis
                description_summary TEXT,
                pros TEXT,
                cons TEXT,

                -- Commute (computed)
                distance_km REAL,
                commute_time_bike_min INTEGER,
                commute_time_transit_min INTEGER,
                commute_time_driving_min INTEGER,
                transit_transfers INTEGER,
                bike_route_coords TEXT,  -- JSON array

                -- Neighborhood scores
                neighborhood_name TEXT,
                neighborhood_safety INTEGER,
                neighborhood_green_space INTEGER,
                neighborhood_amenities INTEGER,
                neighborhood_restaurants INTEGER,
                neighborhood_family_friendly INTEGER,
                neighborhood_expat_friendly INTEGER,
                neighborhood_overall REAL
            )
        """)

        # Index for faster URL lookups (deduplication)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_listing_url ON listings(listing_url)
        """)

        # Index for filtering by source
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_source_site ON listings(source_site)
        """)

        # Index for price range queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_price ON listings(price_eur)
        """)

        # Migration: Add transit_transfers column if it doesn't exist
        try:
            cursor.execute("ALTER TABLE listings ADD COLUMN transit_transfers INTEGER")
        except sqlite3.OperationalError:
            pass  # Column already exists

        self.conn.commit()

    def upsert_listing(self, listing: dict | RentalListing) -> tuple[int, bool]:
        """Insert or update a listing, deduplicating by URL.

        Args:
            listing: Listing data as dict or RentalListing model

        Returns:
            Tuple of (listing_id, is_new) where is_new is True if inserted, False if updated
        """
        if isinstance(listing, RentalListing):
            data = listing.model_dump()
        else:
            data = dict(listing)

        url = data.get("listing_url")
        if not url:
            raise ValueError("Listing must have a listing_url")

        # Convert bike_route_coords list to JSON string
        if data.get("bike_route_coords"):
            data["bike_route_coords"] = json.dumps(data["bike_route_coords"])

        # Convert datetime to string
        if isinstance(data.get("scraped_at"), datetime):
            data["scraped_at"] = data["scraped_at"].isoformat()

        # Filter to only include columns that exist in the database schema
        data = {k: v for k, v in data.items() if k in self.DB_COLUMNS}

        cursor = self.conn.cursor()

        # Check if listing exists
        cursor.execute("SELECT id FROM listings WHERE listing_url = ?", (url,))
        existing = cursor.fetchone()

        if existing:
            # Update existing listing
            listing_id = existing["id"]
            data["last_seen_at"] = datetime.now().isoformat()

            # Build UPDATE statement dynamically
            set_clauses = []
            values = []
            for key, value in data.items():
                if key not in ("listing_url", "id") and value is not None:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)

            if set_clauses:
                values.append(url)
                cursor.execute(
                    f"UPDATE listings SET {', '.join(set_clauses)} WHERE listing_url = ?",
                    values
                )
                self.conn.commit()

            return listing_id, False
        else:
            # Insert new listing
            columns = [k for k in data.keys() if k != "id" and data[k] is not None]
            placeholders = ["?" for _ in columns]
            values = [data[k] for k in columns]

            cursor.execute(
                f"INSERT INTO listings ({', '.join(columns)}) VALUES ({', '.join(placeholders)})",
                values
            )
            self.conn.commit()

            return cursor.lastrowid, True

    def bulk_upsert(self, listings: list[dict | RentalListing]) -> tuple[int, int]:
        """Insert or update multiple listings.

        Args:
            listings: List of listing data

        Returns:
            Tuple of (new_count, updated_count)
        """
        new_count = 0
        updated_count = 0
        error_count = 0

        for listing in listings:
            try:
                _, is_new = self.upsert_listing(listing)
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                error_count += 1
                # Log to stderr for debugging (won't appear in normal output)
                import sys
                print(f"  [DB ERROR] {type(e).__name__}: {e}", file=sys.stderr)

        return new_count, updated_count

    def get_all_listings(
        self,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        source_site: Optional[str] = None,
        min_surface: Optional[float] = None,
        min_rooms: Optional[int] = None,
        min_neighborhood_score: Optional[float] = None,
    ) -> list[dict]:
        """Retrieve listings with optional filters.

        Args:
            min_price: Minimum price filter
            max_price: Maximum price filter
            source_site: Filter by source site
            min_surface: Minimum surface area filter
            min_rooms: Minimum rooms filter
            min_neighborhood_score: Minimum neighborhood score filter

        Returns:
            List of listings as dicts
        """
        cursor = self.conn.cursor()

        where_clauses = []
        params = []

        if min_price is not None:
            where_clauses.append("(price_eur IS NULL OR price_eur >= ?)")
            params.append(min_price)

        if max_price is not None:
            where_clauses.append("(price_eur IS NULL OR price_eur <= ?)")
            params.append(max_price)

        if source_site:
            where_clauses.append("source_site = ?")
            params.append(source_site)

        if min_surface is not None:
            where_clauses.append("(surface_m2 IS NULL OR surface_m2 >= ?)")
            params.append(min_surface)

        if min_rooms is not None:
            where_clauses.append("(rooms IS NULL OR rooms >= ?)")
            params.append(min_rooms)

        if min_neighborhood_score is not None:
            where_clauses.append("(neighborhood_overall IS NULL OR neighborhood_overall >= ?)")
            params.append(min_neighborhood_score)

        query = "SELECT * FROM listings"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY scraped_at DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert rows to dicts and parse JSON fields
        listings = []
        for row in rows:
            listing = dict(row)
            # Parse bike_route_coords from JSON
            if listing.get("bike_route_coords"):
                try:
                    listing["bike_route_coords"] = json.loads(listing["bike_route_coords"])
                except json.JSONDecodeError:
                    listing["bike_route_coords"] = None
            listings.append(listing)

        return listings

    def get_listing_by_url(self, url: str) -> Optional[dict]:
        """Get a specific listing by URL.

        Args:
            url: Listing URL

        Returns:
            Listing dict or None if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM listings WHERE listing_url = ?", (url,))
        row = cursor.fetchone()

        if row:
            listing = dict(row)
            if listing.get("bike_route_coords"):
                try:
                    listing["bike_route_coords"] = json.loads(listing["bike_route_coords"])
                except json.JSONDecodeError:
                    listing["bike_route_coords"] = None
            return listing
        return None

    def get_listing_count(self) -> int:
        """Get total number of listings in database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM listings")
        return cursor.fetchone()[0]

    def get_sources_summary(self) -> dict[str, int]:
        """Get count of listings per source site."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT source_site, COUNT(*) as count
            FROM listings
            GROUP BY source_site
            ORDER BY count DESC
        """)
        return {row["source_site"]: row["count"] for row in cursor.fetchall()}

    def delete_listing(self, url: str) -> bool:
        """Delete a listing by URL.

        Args:
            url: Listing URL to delete

        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM listings WHERE listing_url = ?", (url,))
        self.conn.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        """Close the database connection."""
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
