"""F077 Phase 2 — content-based listing recommendations.

Pure read-side service that scores active listings against the
caller's recent view history (``ListingViewEvent``) and returns the
top-N. Designed to be cheap (a handful of indexed scans + one in-Python
aggregation) and resilient — if the user has no view history we degrade
gracefully to a newest-first feed slice so the buyer home tab is never
empty.

Scoring logic (see ``F077`` Phase 2 spec):

1. Pull the user's ``ListingViewEvent`` rows from the last 30 days.
2. Aggregate by ``(district, property_type, rooms)``; the frequency
   becomes the combo's weight.
3. Take the user's top-3 combos and score every active listing:

   - +3 for a district hit on any top-3 combo
   - +2 for a property_type hit on any top-3 combo
   - +1 for a rooms hit on any top-3 combo
   - +1 if the listing's price is within ±20% of the median price
     across the user's viewed listings

4. Exclude listings the user has already viewed.
5. Order by score DESC, ``created_at`` DESC for tie-breakers.
6. Return the top ``limit`` rows.

The function takes the same care as ``_postgres_listings_search``:
only ACTIVE / APPROVED / non-deleted listings are considered, master
records only (``master_record_id IS NULL``), and the ``images`` /
``seller`` relationships are eager-loaded for the response builder.
"""

from __future__ import annotations

import statistics
from collections import Counter
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    Listing,
    ListingStatus,
    ListingViewEvent,
    ModerationStatus,
)

# Window over which the user's history is read. Older events are
# considered stale signal and ignored.
_HISTORY_WINDOW_DAYS = 30

# Number of top combos to use when scoring candidates.
_TOP_COMBOS = 3

# Score weights (see docstring).
_W_DISTRICT = 3
_W_PROPERTY_TYPE = 2
_W_ROOMS = 1
_W_PRICE = 1

# How wide the "in price band" check is (fraction of median).
_PRICE_BAND = 0.20


def _active_listings_query():
    """Base SELECT for B2C-visible listings.

    Mirrors the eligibility predicate used by ``/listings`` and
    ``/listings/feed`` so what the user sees in the Recommended tab can
    only be a strict subset of what the main feed would expose.
    """
    return select(Listing).where(
        Listing.status == ListingStatus.ACTIVE,
        Listing.moderation_status == ModerationStatus.APPROVED,
        Listing.deleted_at.is_(None),
        Listing.master_record_id.is_(None),
    )


async def _default_feed_top_n(
    db: AsyncSession, limit: int
) -> List[Listing]:
    """Graceful fallback when there's no personalisation signal.

    Returns the most recent active listings, ordered the same way the
    public feed orders them (boosted first, then newest), so a brand-new
    user opening the Recommended tab sees something useful instead of
    an empty state.
    """
    query = (
        _active_listings_query()
        .order_by(Listing.is_boosted.desc(), Listing.created_at.desc())
        .limit(limit)
        .options(selectinload(Listing.images), selectinload(Listing.seller))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_recommended_listings(
    db: AsyncSession,
    user_id: UUID,
    limit: int = 20,
) -> List[Listing]:
    """Return the recommended listings for ``user_id`` (best-first).

    Falls back to the default feed top-N when the user has no view
    history — see module docstring for the full algorithm.
    """
    # ── 1. Pull the user's recent view events ───────────────────────
    cutoff = datetime.utcnow() - timedelta(days=_HISTORY_WINDOW_DAYS)
    history_q = (
        select(ListingViewEvent.listing_id)
        .where(
            ListingViewEvent.user_id == user_id,
            ListingViewEvent.viewed_at >= cutoff,
        )
    )
    history_res = await db.execute(history_q)
    viewed_ids: List[UUID] = [row for row in history_res.scalars().all()]

    if not viewed_ids:
        # No personalisation signal — graceful degradation.
        return await _default_feed_top_n(db, limit)

    # Hydrate the viewed listings so we can aggregate combos and price
    # median. We deliberately do not filter on status here — a now-paused
    # listing the user previously viewed still tells us about their
    # preference profile.
    viewed_q = select(Listing).where(Listing.id.in_(set(viewed_ids)))
    viewed_res = await db.execute(viewed_q)
    viewed_listings: List[Listing] = list(viewed_res.scalars().all())

    if not viewed_listings:
        # History rows exist but the listings have been hard-deleted.
        # Treat as no-signal — degrade gracefully.
        return await _default_feed_top_n(db, limit)

    # ── 2. Aggregate combos by frequency ────────────────────────────
    # A combo is keyed by (district, property_type_value, rooms). We
    # tolerate None on any leg — the listing simply won't contribute a
    # district / property_type / rooms boost for that combo.
    combo_counter: Counter = Counter()
    for listing in viewed_listings:
        pt = listing.property_type.value if listing.property_type else None
        combo_counter[(listing.district, pt, listing.rooms)] += 1

    top_combos = [combo for combo, _ in combo_counter.most_common(_TOP_COMBOS)]
    top_districts = {c[0] for c in top_combos if c[0] is not None}
    top_property_types = {c[1] for c in top_combos if c[1] is not None}
    top_rooms = {c[2] for c in top_combos if c[2] is not None}

    # Price median across all viewed listings with a non-null price.
    viewed_prices = [
        listing.price for listing in viewed_listings if listing.price is not None
    ]
    price_band: Optional[tuple[float, float]] = None
    if viewed_prices:
        median = statistics.median(viewed_prices)
        price_band = (median * (1 - _PRICE_BAND), median * (1 + _PRICE_BAND))

    # ── 3. Candidate set ────────────────────────────────────────────
    # Exclude what the user has already seen. We pull a generous slice
    # (limit * 10, capped) of recent active listings so we have enough
    # to rank without paying for a full-table scan.
    viewed_id_set = set(viewed_ids)
    candidate_cap = max(limit * 10, 100)

    cand_q = (
        _active_listings_query()
        .where(Listing.id.notin_(viewed_id_set))
        .order_by(Listing.created_at.desc())
        .limit(candidate_cap)
        .options(selectinload(Listing.images), selectinload(Listing.seller))
    )
    cand_res = await db.execute(cand_q)
    candidates: List[Listing] = list(cand_res.scalars().all())

    if not candidates:
        return []

    # ── 4. Score every candidate ────────────────────────────────────
    def _score(listing: Listing) -> int:
        score = 0
        if listing.district and listing.district in top_districts:
            score += _W_DISTRICT
        pt = listing.property_type.value if listing.property_type else None
        if pt and pt in top_property_types:
            score += _W_PROPERTY_TYPE
        if listing.rooms is not None and listing.rooms in top_rooms:
            score += _W_ROOMS
        if (
            price_band is not None
            and listing.price is not None
            and price_band[0] <= listing.price <= price_band[1]
        ):
            score += _W_PRICE
        return score

    scored: List[tuple[int, datetime, Listing]] = [
        (_score(listing), listing.created_at, listing) for listing in candidates
    ]

    # ── 5. Sort: score DESC, created_at DESC for ties. ──────────────
    scored.sort(key=lambda x: (-x[0], -x[1].timestamp()))

    # ── 6. Take the top `limit`. ────────────────────────────────────
    return [listing for _score_val, _ts, listing in scored[:limit]]
