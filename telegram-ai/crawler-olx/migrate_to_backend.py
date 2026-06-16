"""
Migrate OLX crawler JSON files to the Real Estate backend.

Reads all JSON files from output/json/ and POSTs them as a bulk import
to the backend's /api/v1/crawler/olx/import endpoint.

Usage:
    python migrate_to_backend.py [--backend-url http://localhost:8000]
"""
import argparse
import json
import sys
from pathlib import Path

import requests

OUTPUT_DIR = Path(__file__).parent / "output" / "json"
DEFAULT_BACKEND_URL = "http://localhost:8000"


def load_json_files(directory: Path) -> list[dict]:
    """Load all JSON files from the output directory."""
    listings = []
    json_files = sorted(directory.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {directory}")
        return []

    for filepath in json_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            listings.append(data)
            print(f"  Loaded: {filepath.name}")
        except (json.JSONDecodeError, OSError) as e:
            print(f"  SKIP (error): {filepath.name} — {e}")

    return listings


def migrate(backend_url: str):
    """Load JSON files and POST to the backend."""
    print(f"Loading JSON files from: {OUTPUT_DIR}")
    listings = load_json_files(OUTPUT_DIR)

    if not listings:
        print("Nothing to migrate.")
        sys.exit(0)

    print(f"\nFound {len(listings)} listings. Sending to backend...")

    url = f"{backend_url}/api/v1/crawler/olx/import"
    payload = {"listings": listings}

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
    except requests.ConnectionError:
        print(f"\nERROR: Cannot connect to backend at {backend_url}")
        print("Make sure the backend is running.")
        sys.exit(1)
    except requests.HTTPError as e:
        print(f"\nERROR: Backend returned {response.status_code}")
        print(response.text[:1000])
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
    parser = argparse.ArgumentParser(description="Migrate OLX JSON files to Real Estate backend")
    parser.add_argument(
        "--backend-url",
        default=DEFAULT_BACKEND_URL,
        help=f"Backend base URL (default: {DEFAULT_BACKEND_URL})",
    )
    args = parser.parse_args()
    migrate(args.backend_url)
