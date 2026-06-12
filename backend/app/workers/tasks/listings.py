"""Listing-related Celery tasks."""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task
def check_expired_listings() -> Dict[str, Any]:
    """Check and mark expired listings.

    Returns:
        Result dict with updated counts
    """
    logger.info("Checking for expired listings")

    # TODO: Implement actual database query to find and update expired listings
    # This should:
    # 1. Find listings where expires_at < now() and status = 'active'
    # 2. Update their status to 'expired'

    return {
        "checked_at": datetime.utcnow().isoformat(),
        "expired_count": 0,
    }


@celery_app.task
def update_exchange_rates() -> Dict[str, Any]:
    """Update USD to UZS exchange rate from Central Bank of Uzbekistan.

    Returns:
        Result dict with exchange rate info
    """
    try:
        with httpx.Client() as client:
            response = client.get(
                settings.exchange_rate_api_url,
                timeout=10.0,
            )
            response.raise_for_status()

            data = response.json()

            # Find USD rate
            usd_rate = None
            for currency in data:
                if currency.get("Ccy") == "USD":
                    usd_rate = float(currency.get("Rate", 0))
                    break

            if usd_rate:
                # Store the rate in Redis (24h TTL)
                import redis as sync_redis

                try:
                    r = sync_redis.Redis(
                        host=settings.redis_host,
                        port=settings.redis_port,
                        db=settings.redis_db,
                        decode_responses=True,
                    )
                    r.set("rate:usd_uzs", str(usd_rate), ex=86400)
                    logger.info(
                        f"Stored exchange rate in Redis: 1 USD = {usd_rate} UZS"
                    )
                except Exception as redis_exc:
                    logger.warning(f"Failed to store rate in Redis: {redis_exc}")

                return {
                    "success": True,
                    "usd_uzs_rate": usd_rate,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            else:
                logger.warning("USD rate not found in API response")
                return {
                    "success": False,
                    "error": "USD rate not found",
                    "fallback_rate": settings.exchange_rate_fallback,
                }

    except Exception as exc:
        logger.error(f"Failed to update exchange rates: {exc}")
        return {
            "success": False,
            "error": str(exc),
            "fallback_rate": settings.exchange_rate_fallback,
        }


@celery_app.task
def sync_to_meilisearch() -> Dict[str, Any]:
    """Reconcile the Meilisearch index from Postgres (periodic safety net).

    In steady state the per-write hooks (``search_index.index_listing`` /
    ``delete_listing``, called inline from the listings API) keep the index
    current. This beat job covers the two gaps those hooks cannot:

    1. **Bootstrap.** ``init_meilisearch_index`` (re)creates the index and
       pushes the filterable/sortable/searchable attribute config. Without
       a sortable ``created_at`` a fresh index rejects the bot's
       ``sort=["created_at:desc"]`` query, so every inline / ``/search``
       lookup silently returns zero results.
    2. **Backfill.** Streams every ACTIVE listing into the index, so a fresh
       deployment (or one recovering from a Meili data loss) becomes
       searchable without a manual script run.

    Idempotent (Meili upserts by primary key) and safe-fallback: a Meili
    outage logs a warning and returns zero counts — Postgres stays the
    source of truth.

    Returns:
        Result dict with sync counts
    """
    from app.db.database import async_session_maker
    from app.services.search_index import (
        backfill_all_listings,
        init_meilisearch_index,
    )

    logger.info("Syncing listings to Meilisearch")

    if not init_meilisearch_index():
        logger.warning(
            "sync_to_meilisearch: Meilisearch unavailable; skipping backfill"
        )
        return {
            "synced_at": datetime.utcnow().isoformat(),
            "documents_indexed": 0,
            "failed_count": 0,
        }

    async def _run() -> Dict[str, Any]:
        async with async_session_maker() as session:
            return await backfill_all_listings(session)

    result = asyncio.run(_run())
    logger.info(
        "Meilisearch sync done: indexed=%d failed=%d",
        result["indexed_count"],
        result["failed_count"],
    )
    return {
        "synced_at": datetime.utcnow().isoformat(),
        "documents_indexed": result["indexed_count"],
        "failed_count": result["failed_count"],
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def index_listing_in_meilisearch(self, listing_id: str) -> Dict[str, Any]:
    """Index a single listing in Meilisearch.

    Args:
        listing_id: UUID of the listing to index

    Returns:
        Result dict with index status
    """
    try:
        logger.info(f"Indexing listing {listing_id} in Meilisearch")

        # TODO: Implement actual indexing
        # This should:
        # 1. Fetch listing from database
        # 2. Transform to search document
        # 3. Add to Meilisearch index

        return {
            "success": True,
            "listing_id": listing_id,
            "indexed_at": datetime.utcnow().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Failed to index listing {listing_id}: {exc}")
        self.retry(exc=exc)


@celery_app.task
def generate_dedup_signature(
    listing_id: str,
    contact_phone: Optional[str],
    address: Optional[str],
    price: Optional[int],
    rooms: Optional[int],
    area: Optional[float],
) -> Dict[str, Any]:
    """Generate a deduplication signature for a listing.

    The signature is based on key identifying fields to detect duplicate listings.

    Args:
        listing_id: UUID of the listing
        contact_phone: Contact phone number
        address: Property address
        price: Listing price
        rooms: Number of rooms
        area: Total area

    Returns:
        Result dict with signature
    """
    # Normalize phone number
    normalized_phone = ""
    if contact_phone:
        normalized_phone = "".join(c for c in contact_phone if c.isdigit())[-9:]

    # Normalize address
    normalized_address = ""
    if address:
        normalized_address = address.lower().strip()

    # Create signature components
    components = [
        normalized_phone,
        normalized_address,
        str(price) if price else "",
        str(rooms) if rooms else "",
        str(int(area)) if area else "",
    ]

    # Generate hash
    signature_string = "|".join(components)
    signature = hashlib.sha256(signature_string.encode()).hexdigest()

    logger.info(
        f"Generated dedup signature for listing {listing_id}: {signature[:16]}..."
    )

    return {
        "listing_id": listing_id,
        "signature": signature,
        "components": components,
    }


@celery_app.task
def process_listing_images(listing_id: str, image_urls: list) -> Dict[str, Any]:
    """Process and optimize listing images.

    Args:
        listing_id: UUID of the listing
        image_urls: List of original image URLs

    Returns:
        Result dict with processed image info
    """
    logger.info(f"Processing {len(image_urls)} images for listing {listing_id}")

    # TODO: Implement actual image processing
    # This should:
    # 1. Download images
    # 2. Generate thumbnails (150x150)
    # 3. Generate medium size (600x600)
    # 4. Upload to S3
    # 5. Update listing_images table

    return {
        "listing_id": listing_id,
        "total_images": len(image_urls),
        "processed_count": 0,
    }


@celery_app.task
def update_listing_statistics() -> Dict[str, Any]:
    """Update aggregate statistics for listings.

    This task calculates and caches statistics like:
    - Total active listings by type
    - Average prices by region/district
    - Popular search filters

    Returns:
        Result dict with statistics
    """
    logger.info("Updating listing statistics")

    # TODO: Implement actual statistics calculation
    # This should query the database and cache results in Redis

    return {
        "updated_at": datetime.utcnow().isoformat(),
        "statistics_updated": False,
    }
