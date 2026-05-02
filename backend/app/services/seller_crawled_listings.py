"""Service for querying crawled listings matched to a seller's phone number."""

import logging
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OLXListing, TelegramListing

logger = logging.getLogger(__name__)


async def get_crawled_stats(
    db: AsyncSession,
    phone_suffix: str,
) -> dict:
    """Get counts of crawled listings matching a phone suffix.

    Args:
        db: Database session.
        phone_suffix: Last 9 digits of the seller's phone.

    Returns:
        Dict with olx_count, telegram_count, total_count.
    """
    olx_q = (
        select(func.count())
        .select_from(OLXListing)
        .where(
            func.right(OLXListing.contact_phone, 9) == phone_suffix,
            OLXListing.converted_listing_id.is_(None),
            OLXListing.rejected_by_seller_id.is_(None),
        )
    )
    tg_q = (
        select(func.count())
        .select_from(TelegramListing)
        .where(
            func.right(TelegramListing.contact_phone, 9) == phone_suffix,
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
    phone_suffix: str,
    page: int = 1,
    per_page: int = 20,
    listing_type: Optional[str] = None,
) -> Tuple[List[OLXListing], int]:
    """Get paginated OLX listings matching a phone suffix.

    Returns:
        Tuple of (items, total_count).
    """
    base = select(OLXListing).where(
        func.right(OLXListing.contact_phone, 9) == phone_suffix,
        OLXListing.converted_listing_id.is_(None),
        OLXListing.rejected_by_seller_id.is_(None),
    )

    if listing_type:
        base = base.where(OLXListing.listing_type == listing_type)

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginated items
    offset = (page - 1) * per_page
    items_q = base.order_by(OLXListing.crawled_at.desc()).offset(offset).limit(per_page)
    items = (await db.execute(items_q)).scalars().all()

    return list(items), total


async def get_telegram_listings(
    db: AsyncSession,
    phone_suffix: str,
    page: int = 1,
    per_page: int = 20,
    listing_type: Optional[str] = None,
) -> Tuple[List[TelegramListing], int]:
    """Get paginated Telegram listings matching a phone suffix.

    Returns:
        Tuple of (items, total_count).
    """
    base = select(TelegramListing).where(
        func.right(TelegramListing.contact_phone, 9) == phone_suffix,
        TelegramListing.converted_listing_id.is_(None),
        TelegramListing.rejected_by_seller_id.is_(None),
    )

    if listing_type:
        base = base.where(TelegramListing.listing_type == listing_type)

    # Total count
    count_q = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginated items
    offset = (page - 1) * per_page
    items_q = (
        base.order_by(TelegramListing.created_at.desc()).offset(offset).limit(per_page)
    )
    items = (await db.execute(items_q)).scalars().all()

    return list(items), total


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
