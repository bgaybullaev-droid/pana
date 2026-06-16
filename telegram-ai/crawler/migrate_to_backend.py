"""
Migrate Telegram crawler CSV to the Real Estate backend.

Reads the CSV from output/real_estate_listings.csv and POSTs listings
to the backend's /api/v1/crawler/telegram/import endpoint.

Usage:
    python migrate_to_backend.py [--backend-url http://localhost:8001]
"""
import argparse
import csv
import sys
from pathlib import Path

import requests

CSV_PATH = Path(__file__).parent / "output" / "real_estate_listings.csv"
IMAGES_DIR = Path(__file__).parent / "output"
DEFAULT_BACKEND_URL = "http://localhost:8001"


def parse_csv(filepath: Path) -> list[dict]:
    """Read the CSV and convert each row to a TelegramListingImport payload."""
    listings: list[dict] = []

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            # Skip rows missing required fields
            property_type = (row.get("property_type") or "").strip()
            listing_type = (row.get("listing_type") or "").strip()
            price_raw = (row.get("price") or "").strip()

            if not property_type or not listing_type or not price_raw:
                print(f"  SKIP row {i}: missing property_type/listing_type/price")
                continue

            try:
                price = float(price_raw)
            except ValueError:
                print(f"  SKIP row {i}: invalid price '{price_raw}'")
                continue

            if price <= 0:
                print(f"  SKIP row {i}: price <= 0")
                continue

            currency = (row.get("currency") or "USD").strip() or "USD"

            # Parse optional numeric fields
            rooms = _parse_int(row.get("rooms"))
            area_sqm = _parse_float(row.get("area_sqm"))
            floor = _parse_int(row.get("floor"))
            total_floors = _parse_int(row.get("total_floors"))
            message_id = _parse_int(row.get("message_id"))

            # Parse amenities from comma-separated string
            amenities_raw = (row.get("amenities") or "").strip()
            amenities = [a.strip() for a in amenities_raw.split(",") if a.strip()] if amenities_raw else None

            # Parse image paths into URL list (local relative paths)
            image_paths_raw = (row.get("image_paths") or "").strip()
            images = None
            if image_paths_raw:
                images = [p.strip() for p in image_paths_raw.split(";") if p.strip()]

            listing = {
                "property_type": property_type,
                "listing_type": listing_type,
                "price": price,
                "currency": currency,
                "rooms": rooms,
                "area_sqm": area_sqm,
                "floor": floor,
                "total_floors": total_floors,
                "district": (row.get("district") or "").strip() or None,
                "address": (row.get("address") or "").strip() or None,
                "description": (row.get("description") or "").strip() or None,
                "amenities": amenities,
                "contact_phone": (row.get("contact_phone") or "").strip() or None,
                "confidence": None,
                "images": images,
                "raw_text": (row.get("raw_text") or "").strip() or None,
                "source_channel": (row.get("channel") or "").strip() or None,
                "message_id": message_id,
            }

            listings.append(listing)
            print(f"  Parsed row {i}: {property_type} / {listing_type} / {price} {currency} ({row.get('channel', '')})")

    return listings


def _parse_int(val: str | None) -> int | None:
    if not val or not val.strip():
        return None
    try:
        return int(float(val.strip()))
    except (ValueError, TypeError):
        return None


def _parse_float(val: str | None) -> float | None:
    if not val or not val.strip():
        return None
    try:
        return float(val.strip())
    except (ValueError, TypeError):
        return None


def migrate(backend_url: str):
    """Load CSV and POST to the backend."""
    print(f"Reading CSV: {CSV_PATH}")

    if not CSV_PATH.exists():
        print(f"ERROR: CSV file not found at {CSV_PATH}")
        sys.exit(1)

    listings = parse_csv(CSV_PATH)

    if not listings:
        print("Nothing to migrate.")
        sys.exit(0)

    print(f"\nParsed {len(listings)} valid listings. Sending to backend...")

    url = f"{backend_url}/api/v1/crawler/telegram/import"
    payload = {"listings": listings}

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
    except requests.ConnectionError:
        print(f"\nERROR: Cannot connect to backend at {backend_url}")
        print("Make sure the backend is running.")
        sys.exit(1)
    except requests.HTTPError:
        print(f"\nERROR: Backend returned {response.status_code}")
        print(response.text[:2000])
        sys.exit(1)

    result = response.json()
    print(f"\nImport complete:")
    print(f"  Total:      {result['total']}")
    print(f"  Created:    {result['created']}")
    print(f"  Duplicates: {result['duplicates']}")
    print(f"  Errors:     {result['errors']}")

    if result["errors"] > 0:
        for r in result["results"]:
            if not r["success"]:
                print(f"  Error at index {r['index']}: {r['error']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Telegram CSV to Real Estate backend")
    parser.add_argument(
        "--backend-url",
        default=DEFAULT_BACKEND_URL,
        help=f"Backend base URL (default: {DEFAULT_BACKEND_URL})",
    )
    args = parser.parse_args()
    migrate(args.backend_url)
