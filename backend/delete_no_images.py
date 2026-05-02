"""
Delete crawler listings that have no images from the database.

Usage:
    cd backend && source venv/bin/activate && python delete_no_images.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


async def main():
    from app.db.database import async_session_maker
    from app.db.models import TelegramListing, OLXListing
    from sqlalchemy import select, or_

    async with async_session_maker() as db:
        # Delete Telegram listings without images
        result = await db.execute(
            select(TelegramListing).where(
                or_(
                    TelegramListing.images.is_(None),
                    TelegramListing.images == [],
                )
            )
        )
        tg_no_images = result.scalars().all()
        for listing in tg_no_images:
            await db.delete(listing)
        print(f"Deleted {len(tg_no_images)} Telegram listings without images")

        # Delete OLX listings without images
        result = await db.execute(
            select(OLXListing).where(
                or_(
                    OLXListing.images.is_(None),
                    OLXListing.images == [],
                )
            )
        )
        olx_no_images = result.scalars().all()
        for listing in olx_no_images:
            await db.delete(listing)
        print(f"Deleted {len(olx_no_images)} OLX listings without images")

        await db.commit()

        # Show remaining counts
        tg_count = (await db.execute(select(TelegramListing))).scalars().all()
        olx_count = (await db.execute(select(OLXListing))).scalars().all()
        print(f"\nRemaining: {len(tg_count)} Telegram, {len(olx_count)} OLX")


if __name__ == "__main__":
    asyncio.run(main())
