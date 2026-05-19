"""Service for querying crawled listings matched to a seller's phone number.

Block C V2.0 (C4): the matching key is now a SET of phone suffixes
(seller's primary + any additional verified phones from user_phones),
not a single suffix. Existing single-phone callers continue to work —
the helper functions accept either ``str`` or ``List[str]`` for the
phone-suffix argument and normalise to a list internally.
"""

import logging
from typing import List, Optional, Tuple, Union

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OLXListing, TelegramListing

logger = logging.getLogger(__name__)


def _coerce_suffixes(value: Union[str, List[str]]) -> List[str]:
    """Backward-compat shim: accept str or List[str], emit list."""
    if isinstance(value, str):
        return [value] if value else []
    return [s for s in value if s]


async def get_crawled_stats(
    db: AsyncSession,
    phone_suffix: Union[str, List[str]],
) -> dict:
    """Counts of crawled listings matching ANY of the seller's phone suffixes.

    Args:
        db: Database session.
        phone_suffix: Last 9 digits of any of the seller's verified phones.
                      Accepts str (single, backward-compat) or List[str]
                      (multi-phone, C4).
    Returns:
        Dict with olx_count, telegram_count, total_count.
    """
    suffixes = _coerce_suffixes(phone_suffix)
    if not suffixes:
        return {"olx_count": 0, "telegram_count": 0, "total_count": 0}

    olx_q = (
        select(func.count())
        .select_from(OLXListing)
        .where(
            func.right(OLXListing.contact_phone, 9).in_(suffixes),
            OLXListing.converted_listing_id.is_(None),
            OLXListing.rejected_by_seller_id.is_(None),
        )
    )
    tg_q = (
        select(func.count())
        .select_from(TelegramListing)
        .where(
            func.right(TelegramListing.contact_phone, 9).in_(suffixes),
            TelegramListing.converted_listing_id.is_(None),
            TelegramListing.rejected_by_seller_id.is_(None),
        )
    )

    olx_result = await db.execute(olx_q)
    tg_result = await db.execute(tg_q)

    olx_count = olx_result.scalar() or 0
    tg_count = tg_result.scalar() or 0

    return {
        "olx_count": olx_count,
        "telegram_count": tg_count,
        "total_count": olx_count + tg_count,
    }


async def get_olx_listings(
    db: AsyncSession,
    phone_suffix: Union[str, List[str]],
    page: int = 1,
    per_page: int = 20,
    listing_type: Optional[str] = None,
) -> Tuple[List[OLXListing], int]:
    """Paginated OLX listings matching ANY of the seller's phone suffixes."""
    suffixes = _coerce_suffixes(phone_suffix)
    if not suffixes:
        return [], 0

    base = select(OLXListing).where(
        func.right(OLXListing.contact_phone, 9).in_(suffixes),
        OLXListing.converted_listing_id.is_(None),
        OLXListing.rejected_by_seller_id.is_(None),
    )

    if listing_type:
        base = base.where(OLXListing.listing_type == listing_type)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    items_q = base.order_by(OLXListing.crawled_at.desc()).offset(offset).limit(per_page)
    items = (await db.execute(items_q)).scalars().all()

    return list(items), total


async def get_telegram_listings(
    db: AsyncSession,
    phone_suffix: Union[str, List[str]],
    page: int = 1,
    per_page: int = 20,
    listing_type: Optional[str] = None,
) -> Tuple[List[TelegramListing], int]:
    """Paginated Telegram listings matching ANY of the seller's phone suffixes."""
    suffixes = _coerce_suffixes(phone_suffix)
    if not suffixes:
        return [], 0

    base = select(TelegramListing).where(
        func.right(TelegramListing.contact_phone, 9).in_(suffixes),
        TelegramListing.converted_listing_id.is_(None),
        TelegramListing.rejected_by_seller_id.is_(None),
    )

    if listing_type:
        base = base.where(TelegramListing.listing_type == listing_type)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    items_q = (
        base.order_by(TelegramListing.created_at.desc()).offset(offset).limit(per_page)
    )
    items = (await db.execute(items_q)).scalars().all()

    return list(items), total


async def get_phone_suffixes_for_user(
    db: AsyncSession, user_id
) -> List[str]:
    """Return all verified phone suffixes for the user.

    Uses ``user_phones`` (Block C V2.0 / C4). Returns last-9-digit
    suffixes; empty list if user has no verified phones.
    """
    from app.db.models import UserPhone

    rows = (
        await db.execute(
            select(UserPhone.phone).where(UserPhone.user_id == user_id)
        )
    ).scalars().all()

    suffixes: List[str] = []
    for phone in rows:
        if not phone:
            continue
        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) >= 9:
            suffixes.append(digits[-9:])
    return suffixes


# =============================================================================
# Channel-based queries (for Telegram channel sellers)
# =============================================================================


def _channel_match_filter(channel_name: str):
    """Build SQLAlchemy filter for matching source_channel regardless of @ prefix."""
    return (
        func.lower(func.replace(TelegramListing.source_channel, "@", ""))
        == channel_name.lower()
    )


async def get_crawled_stats_by_channel(
    db: AsyncSession,
    channel_name: str,
) -> dict:
    """Get counts of Telegram crawled listings matching a channel name."""
    tg_q = (
        select(func.count())
        .select_from(TelegramListing)
        .where(
            _channel_match_filter(channel_name),
            TelegramListing.converted_listing_id.is_(None),
            TelegramListing.rejected_by_seller_id.is_(None),
        )
    )
    tg_result = await db.execute(tg_q)
    tg_count = tg_result.scalar() or 0

    return {
        "olx_count": 0,
        "telegram_count": tg_count,
        "total_count": tg_count,
    }


async def get_telegram_listings_by_channel(
    db: AsyncSession,
    channel_name: str,
    page: int = 1,
    per_page: int = 20,
    listing_type: Optional[str] = None,
) -> Tuple[List[TelegramListing], int]:
    """Get paginated Telegram listings matching a channel name."""
    base = select(TelegramListing).where(
        _channel_match_filter(channel_name),
        TelegramListing.converted_listing_id.is_(None),
        TelegramListing.rejected_by_seller_id.is_(None),
    )

    if listing_type:
        base = base.where(TelegramListing.listing_type == listing_type)

    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    offset = (page - 1) * per_page
    items_q = (
        base.order_by(TelegramListing.created_at.desc()).offset(offset).limit(per_page)
    )
    items = (await db.execute(items_q)).scalars().all()

    return list(items), total
