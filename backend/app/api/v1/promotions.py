"""Block phase-2 — seller listing promotion purchase endpoints.

Three wallet-gated purchase endpoints, all mounted under
``/seller/listings/{listing_id}/promotions/*``:

- ``POST .../urgent``           — buy the "urgent" badge for a window.
- ``POST .../notify-priority``  — bump this listing to the top of saved-
  search delivery for a window.
- ``POST .../boost``            — boost in the feed for a window
  (uses the pre-existing ``is_boosted`` / ``boost_until`` columns).

Wallet flow
===========
We use ``services.wallet.withdraw`` (which exists; ``spend`` does not).
Each purchase generates an idempotency key derived from
``(seller_id, listing_id, kind, day)`` so identical retries on the same
day collapse to a single charge — but the next day is a fresh charge,
which matches the daily-boost semantics.

Insufficient balance → HTTP 402 with body ``{"error": "insufficient_funds"}``.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_seller
from app.core.exceptions import ForbiddenException, NotFoundException
from app.db.database import get_db
from app.db.models import Listing, Seller, Wallet
from app.services.wallet import InsufficientFunds, withdraw

logger = logging.getLogger(__name__)
router = APIRouter()


# ── pricing (v1 hardcoded; later move to settings) ──────────────────
PRICE_URGENT_UZS = 5_000
PRICE_NOTIFY_PRIORITY_UZS = 20_000
PRICE_BOOST_PER_DAY_UZS = 2_000


# ── request / response schemas ──────────────────────────────────────


class UrgentRequest(BaseModel):
    duration_days: int = Field(default=7, ge=1, le=30)


class NotifyPriorityRequest(BaseModel):
    duration_days: int = Field(default=30, ge=1, le=90)


class BoostRequest(BaseModel):
    duration_days: int = Field(default=1, ge=1, le=14)


class PromotionResponse(BaseModel):
    listing_id: str
    kind: str
    active_until: datetime
    amount_charged: int
    balance_after: int


# ── helpers ─────────────────────────────────────────────────────────


async def _load_owned_listing(
    db: AsyncSession, listing_id: UUID, seller: Seller
) -> Listing:
    """Fetch listing and verify the calling seller owns it."""
    result = await db.execute(select(Listing).where(Listing.id == listing_id))
    listing = result.scalar_one_or_none()
    if listing is None or listing.deleted_at is not None:
        raise NotFoundException("Listing", str(listing_id))
    if listing.seller_id != seller.id:
        raise ForbiddenException("You do not own this listing")
    return listing


def _insufficient_funds_response() -> HTTPException:
    """Build the canonical 402 response used by all three endpoints."""
    return HTTPException(
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
        detail={"error": "insufficient_funds"},
    )


async def _charge_and_apply(
    db: AsyncSession,
    *,
    seller: Seller,
    listing: Listing,
    kind: str,
    amount: int,
    apply_to_listing,
) -> PromotionResponse:
    """Common purchase pipeline: withdraw → mutate listing → commit."""
    # Idempotency key bucketed per-day so retries collapse but next-day
    # re-purchases are real new charges.
    day_bucket = datetime.utcnow().strftime("%Y-%m-%d")
    idem_key = f"promo:{kind}:{seller.id}:{listing.id}:{day_bucket}"

    try:
        tx = await withdraw(
            db,
            user_id=seller.user_id,
            amount=amount,
            idempotency_key=idem_key,
            purpose=f"promotion:{kind}",
            metadata={"listing_id": str(listing.id), "promotion_kind": kind},
        )
    except InsufficientFunds:
        await db.rollback()
        raise _insufficient_funds_response()

    until = apply_to_listing(listing)

    # Re-read wallet balance for the response (withdraw already updated
    # the locked row in this same transaction).
    wallet = (
        await db.execute(
            select(Wallet).where(Wallet.user_id == seller.user_id)
        )
    ).scalar_one()

    await db.commit()

    return PromotionResponse(
        listing_id=str(listing.id),
        kind=kind,
        active_until=until,
        amount_charged=amount,
        balance_after=wallet.current_balance,
    )


# ── endpoints ───────────────────────────────────────────────────────


@router.post(
    "/{listing_id}/promotions/urgent",
    response_model=PromotionResponse,
    summary="Buy the 'urgent' badge for a listing",
)
async def buy_urgent(
    listing_id: UUID,
    body: UrgentRequest,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> PromotionResponse:
    listing = await _load_owned_listing(db, listing_id, seller)

    def _apply(l: Listing) -> datetime:
        until = datetime.utcnow() + timedelta(days=body.duration_days)
        l.has_urgent_badge = True
        l.urgent_until = until
        return until

    return await _charge_and_apply(
        db,
        seller=seller,
        listing=listing,
        kind="urgent",
        amount=PRICE_URGENT_UZS,
        apply_to_listing=_apply,
    )


@router.post(
    "/{listing_id}/promotions/notify-priority",
    response_model=PromotionResponse,
    summary="Bump this listing to the top of saved-search notifications",
)
async def buy_notify_priority(
    listing_id: UUID,
    body: NotifyPriorityRequest,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> PromotionResponse:
    listing = await _load_owned_listing(db, listing_id, seller)

    def _apply(l: Listing) -> datetime:
        until = datetime.utcnow() + timedelta(days=body.duration_days)
        l.notify_priority_until = until
        return until

    return await _charge_and_apply(
        db,
        seller=seller,
        listing=listing,
        kind="notify_priority",
        amount=PRICE_NOTIFY_PRIORITY_UZS,
        apply_to_listing=_apply,
    )


@router.post(
    "/{listing_id}/promotions/boost",
    response_model=PromotionResponse,
    summary="Boost the listing in the buyer feed (per-day pricing)",
)
async def buy_boost(
    listing_id: UUID,
    body: BoostRequest,
    seller: Seller = Depends(get_current_seller),
    db: AsyncSession = Depends(get_db),
) -> PromotionResponse:
    listing = await _load_owned_listing(db, listing_id, seller)

    def _apply(l: Listing) -> datetime:
        until = datetime.utcnow() + timedelta(days=body.duration_days)
        l.is_boosted = True
        l.boost_until = until
        return until

    return await _charge_and_apply(
        db,
        seller=seller,
        listing=listing,
        kind="boost",
        amount=PRICE_BOOST_PER_DAY_UZS * body.duration_days,
        apply_to_listing=_apply,
    )
