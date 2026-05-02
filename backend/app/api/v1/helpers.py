"""Shared helpers for API endpoints."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Listing, OLXListing, TelegramListing


async def find_listing_any_source(db: AsyncSession, listing_id: UUID):
    """Check if a listing exists in any of the three tables (main, telegram, olx)."""
    res = await db.execute(
        select(Listing).where(Listing.id == listing_id, Listing.deleted_at.is_(None))
    )
    listing = res.scalar_one_or_none()
    if listing:
        return listing

    res = await db.execute(
        select(TelegramListing).where(TelegramListing.id == listing_id)
    )
    listing = res.scalar_one_or_none()
    if listing:
        return listing

    res = await db.execute(select(OLXListing).where(OLXListing.id == listing_id))
    return res.scalar_one_or_none()
