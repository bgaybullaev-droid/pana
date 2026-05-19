"""C2 — Live listing-quota helper (Block C decision-pass G2).

Per GRANDFATHERING_POLICY §1, the canonical "billable listings count
per seller" is computed live from `listings` rather than from the
denormalised `Seller.listings_count` field (which is observably broken
across status transitions).

Per Block A V2.0, only ``ACTIVE`` and ``GENERATION_FAILED`` listings
are billable (visible in B2C). Everything else (PAUSED / SOLD / EXPIRED
/ DELETED / PENDING_GENERATION / UNCONFIRMED) does NOT count.

The middleware ``check_can_create_listing`` is gated on
``settings.test_period_active``: during the test period it always
returns true (display-only mode). After the flip, it enforces
``count < free_listings_per_seller`` unless the seller has paid for
the slot — the "paid for the slot" check hooks into C3's Subscription
table once Phase-2 work activates monetization.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_seller
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Listing, ListingStatus, Seller


# Statuses that count toward the per-seller limit. Mirrors the
# buyer-feed gate at backend/app/api/v1/listings.py:1182.
_BILLABLE_STATUSES = (ListingStatus.ACTIVE, ListingStatus.GENERATION_FAILED)


async def get_billable_listing_count(
    seller_id: UUID, db: AsyncSession
) -> int:
    """Number of listings counting toward the seller's plan limit.

    Live query — never reads the denormalised ``Seller.listings_count``
    field (which is observably broken; see TRUTH_LAYER_AUDIT §3.1).
    """
    result = await db.execute(
        select(func.count(Listing.id)).where(
            Listing.seller_id == seller_id,
            Listing.status.in_(_BILLABLE_STATUSES),
            Listing.deleted_at.is_(None),
        )
    )
    return int(result.scalar_one() or 0)


async def get_lifetime_listing_count(
    seller_id: UUID, db: AsyncSession
) -> int:
    """All non-deleted listings, regardless of status.

    Useful for analytics / public profile counters that want to show
    "this seller has had N listings ever" rather than "N currently live".
    """
    result = await db.execute(
        select(func.count(Listing.id)).where(
            Listing.seller_id == seller_id,
            Listing.deleted_at.is_(None),
        )
    )
    return int(result.scalar_one() or 0)


async def can_create_listing(
    seller: Seller, db: AsyncSession
) -> bool:
    """Quota gate. Returns True if the seller may create another listing.

    During the test period (``settings.test_period_active=True``), the
    function always returns True — there is no enforcement.

    After the flip, it enforces ``billable_count < free_listings_per_seller``
    OR the seller has an active paid slot. The paid-slot check is a
    placeholder until C3 Phase-2 activates Subscription billing.
    """
    if settings.test_period_active:
        return True

    billable = await get_billable_listing_count(seller.id, db)
    if billable < settings.free_listings_per_seller:
        return True

    # Phase-2 hook: check Subscription table for an active listing-extra
    # slot. Until C3 Phase-2 wires the subscription consumer, this
    # branch always denies. That's the correct fail-safe.
    return False


async def check_can_create_listing(
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> Seller:
    """FastAPI dependency: enforces quota.

    Returns the seller (so call sites that previously did
    ``seller = Depends(get_current_seller)`` can swap to
    ``seller = Depends(check_can_create_listing)`` with no other
    change).

    Raises 402 Payment Required when over the limit in paid phase.
    During test period this is a no-op pass-through.
    """
    if not await can_create_listing(seller, db):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "quota_exceeded",
                "message": (
                    "Достигнут лимит бесплатных объявлений. "
                    "Оформите подписку или оплатите дополнительный слот."
                ),
                "free_limit": settings.free_listings_per_seller,
                "extra_listing_price_uzs": settings.extra_listing_price_uzs,
            },
        )
    return seller
