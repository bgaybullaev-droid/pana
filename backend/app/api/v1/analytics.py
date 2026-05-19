"""Block phase-2 — admin-only analytics endpoints.

Currently exposes a single read-only ``price-index`` endpoint that
returns the median + IQR USD-equivalent price across closed sales
matching a filter (district, property_type, rooms) inside a recent
window. UZS sales are converted via the cached USD/UZS rate
(``app.utils.price.get_usd_uzs_rate``); we degrade to ``median=None``
when the matched sample is smaller than ``MIN_SAMPLE_SIZE`` rather
than returning a misleading single-row "median".
"""

from __future__ import annotations

import logging
import statistics
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_admin
from app.db.database import get_db
from app.db.models import Listing, ListingSale, User
from app.utils.price import get_usd_uzs_rate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Below this many matched sales the median + IQR are not statistically
# meaningful; we return ``median: None`` so the UI can render an
# "insufficient sample" hint instead of a misleading number.
MIN_SAMPLE_SIZE = 5


class PriceIndexResponse(BaseModel):
    """Median + IQR of recent sold-listing prices, normalised to USD."""

    sample_size: int
    median: Optional[int]
    p25: Optional[int]
    p75: Optional[int]
    currency: str = "USD"
    window_days: int


def _percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolation percentile (matches numpy's default).

    ``sorted_values`` must already be sorted ascending; ``q`` is in
    ``[0, 1]``.
    """
    if not sorted_values:
        raise ValueError("empty input")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac


@router.get("/price-index", response_model=PriceIndexResponse)
async def price_index(
    district: Optional[str] = Query(None, max_length=100),
    property_type: Optional[str] = Query(
        None, pattern="^(apartment|house|commercial|land)$"
    ),
    rooms: Optional[int] = Query(None, ge=0, le=20),
    window_days: int = Query(180, ge=1, le=3650),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
) -> PriceIndexResponse:
    """Median + IQR of recent sold prices (USD-equivalent).

    Filter combinators (district / property_type / rooms) are applied
    against the JOINed ``listings`` row. UZS sales are converted via
    the cached exchange rate; if the rate is unavailable they are
    dropped from the sample to avoid skewing the median.
    """
    cutoff = datetime.utcnow() - timedelta(days=window_days)

    stmt = (
        select(ListingSale.sold_price, ListingSale.sold_currency)
        .join(Listing, Listing.id == ListingSale.listing_id)
        .where(ListingSale.sold_at >= cutoff)
    )
    if district:
        stmt = stmt.where(Listing.district == district)
    if property_type:
        stmt = stmt.where(Listing.property_type == property_type)
    if rooms is not None:
        stmt = stmt.where(Listing.rooms == rooms)

    rows = (await db.execute(stmt)).all()

    if not rows:
        return PriceIndexResponse(
            sample_size=0,
            median=None,
            p25=None,
            p75=None,
            window_days=window_days,
        )

    usd_rate = await get_usd_uzs_rate()
    usd_values: list[float] = []
    for sold_price, sold_currency in rows:
        cur = (sold_currency or "").upper()
        if cur == "USD":
            usd_values.append(float(sold_price))
        elif cur == "UZS":
            if usd_rate and usd_rate > 0:
                usd_values.append(float(sold_price) / usd_rate)
            # else: drop — converting at a zero/negative rate would
            # poison the median.
        # Unknown currency: drop silently. Logging here would be noise
        # because the writer-side schema already enforces USD/UZS.

    sample_size = len(usd_values)
    if sample_size < MIN_SAMPLE_SIZE:
        return PriceIndexResponse(
            sample_size=sample_size,
            median=None,
            p25=None,
            p75=None,
            window_days=window_days,
        )

    usd_values.sort()
    median_val = int(round(statistics.median(usd_values)))
    p25_val = int(round(_percentile(usd_values, 0.25)))
    p75_val = int(round(_percentile(usd_values, 0.75)))

    return PriceIndexResponse(
        sample_size=sample_size,
        median=median_val,
        p25=p25_val,
        p75=p75_val,
        window_days=window_days,
    )
