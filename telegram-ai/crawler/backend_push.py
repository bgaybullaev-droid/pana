"""
Push crawled Telegram listings directly to the Real Estate backend.

Used by FlexibleCrawlerWithHistory to send data in real-time
instead of requiring a manual migration step.
"""

import os
import logging
from pathlib import Path
from typing import Optional

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
except ImportError:
    pass

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
IMPORT_ENDPOINT = f"{BACKEND_URL}/api/v1/crawler/telegram/import"
IMAGE_UPLOAD_ENDPOINT = f"{BACKEND_URL}/api/v1/crawler/images/upload"
TIMEOUT = 30

logger = logging.getLogger(__name__)

# Normalize crawler values → backend enum values before POST
_LISTING_TYPE_NORM = {"sale": "sell", "daily_rent": "rent"}
_PROPERTY_TYPE_NORM = {"office": "commercial"}


def _normalize_enums(listing: dict) -> dict:
    """Normalize listing_type and property_type to match backend enums."""
    lt = listing.get("listing_type", "")
    if lt in _LISTING_TYPE_NORM:
        listing["listing_type"] = _LISTING_TYPE_NORM[lt]
    pt = listing.get("property_type", "")
    if pt in _PROPERTY_TYPE_NORM:
        listing["property_type"] = _PROPERTY_TYPE_NORM[pt]
    return listing


def push_listing(
    extracted_data: dict,
    channel: str,
    message_id: int,
    raw_text: str,
) -> Optional[dict]:
    """Push a single Telegram listing to the backend.

    Args:
        extracted_data: LLM-extracted fields (property_type, price, etc.)
        channel: Telegram channel username
        message_id: Telegram message ID
        raw_text: Original message text

    Returns:
        Import result dict or None on failure.
    """
    listing = {
        "property_type": extracted_data.get("property_type", "unknown"),
        "listing_type": extracted_data.get("listing_type", "sale"),
        "price": extracted_data.get("price", 0),
        "currency": extracted_data.get("currency", "USD"),
        "rooms": extracted_data.get("rooms"),
        "area_sqm": extracted_data.get("area_sqm"),
        "floor": extracted_data.get("floor"),
        "total_floors": extracted_data.get("total_floors"),
        "district": extracted_data.get("district"),
        "address": extracted_data.get("address"),
        "description": extracted_data.get("description"),
        "amenities": extracted_data.get("amenities"),
        "contact_phone": extracted_data.get("contact_phone"),
        "confidence": extracted_data.get("confidence"),
        "images": [],  # Will be filled after image upload
        "raw_text": raw_text,
        "source_channel": channel,
        "message_id": message_id,
        "original_language": extracted_data.get("detected_language", "ru"),
    }

    # Filter None values for optional int/float fields to avoid validation errors
    for key in ("rooms", "floor", "total_floors"):
        if listing[key] is not None:
            try:
                listing[key] = int(listing[key])
            except (ValueError, TypeError):
                listing[key] = None

    for key in ("area_sqm", "price"):
        if listing[key] is not None:
            try:
                listing[key] = float(listing[key])
            except (ValueError, TypeError):
                if key == "price":
                    listing[key] = 0
                else:
                    listing[key] = None

    _normalize_enums(listing)
    payload = {"listings": [listing]}

    try:
        resp = requests.post(IMPORT_ENDPOINT, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        logger.info(
            f"[BACKEND] Pushed listing: created={result['created']}, "
            f"duplicates={result['duplicates']}"
        )
        return result
    except requests.ConnectionError:
        logger.warning(f"[BACKEND] Cannot connect to {BACKEND_URL} — listing not pushed")
        return None
    except Exception as e:
        logger.warning(f"[BACKEND] Push failed: {e}")
        return None


def push_listing_with_images(
    extracted_data: dict,
    channel: str,
    message_id: int,
    raw_text: str,
    image_paths: list[str],
) -> Optional[dict]:
    """Upload images first, then push listing with image URLs.

    Args:
        extracted_data: LLM-extracted fields
        channel: Telegram channel username
        message_id: Telegram message ID
        raw_text: Original message text
        image_paths: List of local file paths to upload

    Returns:
        Import result dict or None on failure.
    """
    # Step 1: Upload images
    image_urls = upload_images(image_paths, source="telegram")

    if not image_urls:
        logger.warning("[BACKEND] No images uploaded — skipping listing (no images = no push)")
        return None

    # Step 2: Build listing payload with image URLs
    listing = {
        "property_type": extracted_data.get("property_type", "unknown"),
        "listing_type": extracted_data.get("listing_type", "sale"),
        "price": extracted_data.get("price", 0),
        "currency": extracted_data.get("currency", "USD"),
        "rooms": extracted_data.get("rooms"),
        "area_sqm": extracted_data.get("area_sqm"),
        "floor": extracted_data.get("floor"),
        "total_floors": extracted_data.get("total_floors"),
        "district": extracted_data.get("district"),
        "address": extracted_data.get("address"),
        "description": extracted_data.get("description"),
        "amenities": extracted_data.get("amenities"),
        "contact_phone": extracted_data.get("contact_phone"),
        "confidence": extracted_data.get("confidence"),
        "images": image_urls,
        "raw_text": raw_text,
        "source_channel": channel,
        "message_id": message_id,
        "original_language": extracted_data.get("detected_language", "ru"),
    }

    # Sanitize numeric fields
    for key in ("rooms", "floor", "total_floors"):
        if listing[key] is not None:
            try:
                listing[key] = int(listing[key])
            except (ValueError, TypeError):
                listing[key] = None

    for key in ("area_sqm", "price"):
        if listing[key] is not None:
            try:
                listing[key] = float(listing[key])
            except (ValueError, TypeError):
                if key == "price":
                    listing[key] = 0
                else:
                    listing[key] = None

    _normalize_enums(listing)
    payload = {"listings": [listing]}

    try:
        resp = requests.post(IMPORT_ENDPOINT, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        logger.info(
            f"[BACKEND] Pushed listing with {len(image_urls)} images: "
            f"created={result['created']}, duplicates={result['duplicates']}"
        )
        return result
    except requests.ConnectionError:
        logger.warning(f"[BACKEND] Cannot connect to {BACKEND_URL} — listing not pushed")
        return None
    except Exception as e:
        logger.warning(f"[BACKEND] Push failed: {e}")
        return None


def upload_images(
    image_paths: list[str],
    source: str = "telegram",
    listing_ref: str = "",
) -> list[str]:
    """Upload image files to the backend and return their public URLs.

    Args:
        image_paths: Local file paths of images to upload.
        source: "telegram" or "olx"
        listing_ref: Optional subdirectory (e.g. OLX listing ID)

    Returns:
        List of public image URLs.
    """
    valid_paths = [p for p in image_paths if os.path.isfile(p)]
    if not valid_paths:
        return []

    try:
        files = []
        open_handles = []
        for path in valid_paths:
            fh = open(path, "rb")
            open_handles.append(fh)
            files.append(("files", (os.path.basename(path), fh, "image/jpeg")))

        data = {"source": source}
        if listing_ref:
            data["listing_ref"] = listing_ref

        resp = requests.post(
            IMAGE_UPLOAD_ENDPOINT, files=files, data=data, timeout=TIMEOUT
        )
        resp.raise_for_status()

        # Close file handles
        for fh in open_handles:
            fh.close()

        urls = resp.json().get("urls", [])
        logger.info(f"[BACKEND] Uploaded {len(urls)} images")
        return urls

    except requests.ConnectionError:
        logger.warning(f"[BACKEND] Cannot connect to {BACKEND_URL} — images not uploaded")
        return []
    except Exception as e:
        logger.warning(f"[BACKEND] Image upload failed: {e}")
        return []
