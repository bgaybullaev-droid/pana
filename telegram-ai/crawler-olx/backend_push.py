"""
Push crawled OLX listings directly to the Real Estate backend.

Used by OLXCrawler to send data in real-time instead of
requiring a manual migration step.
"""

import os
import logging
from pathlib import Path
from typing import Optional

import requests

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=True)
except ImportError:
    pass

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8001")
IMPORT_ENDPOINT = f"{BACKEND_URL}/api/v1/crawler/olx/import"
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
    # Map detected_language → original_language for backend
    if "detected_language" in listing:
        listing.setdefault("original_language", listing.pop("detected_language"))
    return listing


def push_listing(listing_data: dict) -> Optional[dict]:
    """Push a single OLX listing to the backend.

    OLX listings already contain CDN image URLs from the HTML,
    so no image upload step is needed.

    Args:
        listing_data: Extracted listing dict with olx_id, url,
                      crawled_at, property_type, price, images, etc.

    Returns:
        Import result dict or None on failure.
    """
    _normalize_enums(listing_data)
    payload = {"listings": [listing_data]}

    try:
        resp = requests.post(IMPORT_ENDPOINT, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        result = resp.json()
        logger.info(
            f"[BACKEND] Pushed OLX listing {listing_data.get('olx_id')}: "
            f"created={result.get('created', 0)}, "
            f"updated={result.get('updated', 0)}, "
            f"duplicates={result.get('duplicates', 0)}"
        )
        return result
    except requests.ConnectionError:
        logger.warning(f"[BACKEND] Cannot connect to {BACKEND_URL} — listing not pushed")
        return None
    except Exception as e:
        logger.warning(f"[BACKEND] Push failed: {e}")
        return None


def push_listing_with_local_images(
    listing_data: dict,
    image_paths: list[str],
) -> Optional[dict]:
    """Upload local images first, then push listing with image URLs.

    Use this when images have been downloaded locally (e.g. via _download_images).

    Args:
        listing_data: Extracted listing dict
        image_paths: Local file paths of downloaded images

    Returns:
        Import result dict or None on failure.
    """
    olx_id = listing_data.get("olx_id", "")

    # Upload images to backend
    image_urls = upload_images(image_paths, listing_ref=olx_id)

    if not image_urls:
        logger.warning(f"[BACKEND] No images uploaded for {olx_id} — skipping")
        return None

    listing_data = {**listing_data, "images": image_urls}
    return push_listing(listing_data)


def upload_images(
    image_paths: list[str],
    listing_ref: str = "",
) -> list[str]:
    """Upload image files to the backend.

    Args:
        image_paths: Local file paths
        listing_ref: Subdirectory name (e.g. OLX listing ID)

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

        data = {"source": "olx"}
        if listing_ref:
            data["listing_ref"] = listing_ref

        resp = requests.post(
            IMAGE_UPLOAD_ENDPOINT, files=files, data=data, timeout=TIMEOUT
        )
        resp.raise_for_status()

        for fh in open_handles:
            fh.close()

        urls = resp.json().get("urls", [])
        logger.info(f"[BACKEND] Uploaded {len(urls)} OLX images")
        return urls

    except requests.ConnectionError:
        logger.warning(f"[BACKEND] Cannot connect to {BACKEND_URL} — images not uploaded")
        return []
    except Exception as e:
        logger.warning(f"[BACKEND] Image upload failed: {e}")
        return []
