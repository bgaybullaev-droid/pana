"""C1 — Public tariffs endpoint.

Per Block C V2.0 (decision-pass §1, FINAL_IMPLEMENTATION_GATES G1):

- ``GET /tariffs/status`` returns the current monetization configuration
  plus live progress against the activation trigger.
- Cached in Redis for 1 hour. The disclosure block on /seller/tariffs
  tolerates staleness up to that window.

The endpoint is **public** (no auth) so that marketing pages, the bot,
and unauthenticated browsers can read it.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Listing, ListingStatus, ModerationStatus
from app.db.redis import get_redis

router = APIRouter()

_CACHE_KEY = "tariffs:status:v1"
_CACHE_TTL_SECONDS = 3600


class TariffsStatusResponse(BaseModel):
    """Response for ``GET /tariffs/status``.

    All UZS amounts are in smallest currency unit (whole UZS for UZS),
    per MONEY_STORAGE_DECISION.
    """

    test_period_active: bool
    test_period_started_at: Optional[datetime]
    current_listings_total: int
    trigger_listings: int
    trigger_days: int
    days_elapsed: int
    extra_listing_price_uzs: int
    cabinet_subscription_price_uzs: int
    free_listings_per_seller: int


async def _compute_status(db: AsyncSession) -> TariffsStatusResponse:
    """Live computation — without cache. Used internally for warm-up."""
    started_at = settings.test_period_started_at or datetime.utcnow()
    days_elapsed = max(0, (datetime.utcnow() - started_at).days)

    # System-wide active listings count (the trigger condition).
    # Match the buyer-feed gating: ACTIVE + GENERATION_FAILED.
    result = await db.execute(
        select(func.count(Listing.id)).where(
            Listing.status.in_(
                [ListingStatus.ACTIVE, ListingStatus.GENERATION_FAILED]
            ),
            Listing.moderation_status == ModerationStatus.APPROVED,
            Listing.deleted_at.is_(None),
        )
    )
    current_listings_total = int(result.scalar_one() or 0)

    return TariffsStatusResponse(
        test_period_active=settings.test_period_active,
        test_period_started_at=started_at,
        current_listings_total=current_listings_total,
        trigger_listings=settings.monetization_trigger_listings,
        trigger_days=settings.monetization_trigger_days,
        days_elapsed=days_elapsed,
        extra_listing_price_uzs=settings.extra_listing_price_uzs,
        cabinet_subscription_price_uzs=settings.cabinet_subscription_price_uzs,
        free_listings_per_seller=settings.free_listings_per_seller,
    )


@router.get(
    "/status",
    response_model=TariffsStatusResponse,
    summary="Public tariff state + progress (cached 1h)",
)
async def get_tariffs_status(db: AsyncSession = Depends(get_db)) -> TariffsStatusResponse:
    """Public endpoint — no auth required.

    Returns current pricing, test-period state, and progress against the
    activation trigger. Cached in Redis for 1 hour to avoid hitting the
    DB on every page-load.

    Cache invalidation: TTL only. Admin price changes propagate within
    one hour. (Acceptable per spec — the disclosure block is informational.)
    """
    redis = await get_redis()
    cached = await redis.get(_CACHE_KEY)
    if cached:
        try:
            return TariffsStatusResponse(**json.loads(cached))
        except (json.JSONDecodeError, TypeError, ValueError):
            # Cache corruption — recompute and overwrite.
            pass

    response = await _compute_status(db)
    try:
        await redis.setex(_CACHE_KEY, _CACHE_TTL_SECONDS, response.model_dump_json())
    except Exception:
        # Cache write failure is non-fatal; the live computation still works.
        pass
    return response
