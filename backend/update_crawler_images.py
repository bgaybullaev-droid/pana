"""
Update crawler listing images in the database to use proper URLs
served from the backend's /uploads/crawler/ directory.

Usage:
    cd backend && source venv/bin/activate && python update_crawler_images.py
"""
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


BACKEND_BASE = os.environ.get("BACKEND_BASE_URL", "http://localhost:8001")


async def main():
    from app.db.database import async_session_maker
    from app.db.models import TelegramListing, OLXListing
    from sqlalchemy import select

    async with async_session_maker() as db:
        # =====================================================================
        # Update Telegram listings
        # =====================================================================
        print("Updating Telegram listing images...")

        result = await db.execute(
            select(TelegramListing).where(TelegramListing.images.isnot(None))
        )
        listings = result.scalars().all()
        tg_updated = 0

        for listing in listings:
            if not listing.images or not isinstance(listing.images, list):
                continue

            new_images = []
            changed = False
            for img in listing.images:
                if isinstance(img, str) and not img.startswith("http"):
                    filename = img.split("/")[-1]
                    new_url = f"{BACKEND_BASE}/uploads/crawler/telegram/{filename}"
                    new_images.append(new_url)
                    changed = True
                else:
                    new_images.append(img)

            if changed:
                listing.images = new_images
                tg_updated += 1

        print(f"  Updated {tg_updated} / {len(listings)} Telegram listings")

        # =====================================================================
        # Update OLX listings
        # =====================================================================
        print("Updating OLX listing images...")

        result = await db.execute(
            select(OLXListing).where(OLXListing.images.isnot(None))
        )
        listings = result.scalars().all()
        olx_updated = 0

        for listing in listings:
            if not listing.images or not isinstance(listing.images, list):
                continue

            new_images = []
            changed = False
            for img in listing.images:
                if isinstance(img, str) and not img.startswith("http"):
                    filename = img.split("/")[-1]
                    new_url = f"{BACKEND_BASE}/uploads/crawler/olx/{listing.olx_id}/{filename}"
                    new_images.append(new_url)
                    changed = True
                else:
                    new_images.append(img)

            if changed:
                listing.images = new_images
                olx_updated += 1

        print(f"  Updated {olx_updated} / {len(listings)} OLX listings")

        await db.commit()
        print("\nDone! All image URLs updated.")

        # Verify
        result = await db.execute(
            select(TelegramListing).limit(2)
        )
        for listing in result.scalars().all():
            if listing.images:
                print(f"\n  Sample: {listing.images[0]}")
                break


if __name__ == "__main__":
    asyncio.run(main())
