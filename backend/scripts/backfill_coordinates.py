"""Backfill latitude/longitude for existing listings based on district/region data."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.database import async_session_maker

# District-level coordinates (most specific)
DISTRICT_COORDS: dict[str, tuple[float, float]] = {
    # Tashkent districts
    "mirobod": (41.306, 69.274),
    "mirzo_ulugbek": (41.352, 69.335),
    "yakkasaroy": (41.291, 69.266),
    "yakkasaray": (41.291, 69.266),
    "yunusobod": (41.370, 69.279),
    "yunusabad": (41.370, 69.279),
    "chilanzar": (41.262, 69.187),
    "sergeli": (41.210, 69.232),
    "sergeliy": (41.210, 69.232),
    "uchtepa": (41.312, 69.192),
    "almazar": (41.337, 69.222),
    "bektemir": (41.212, 69.326),
    "shaykhontohur": (41.332, 69.243),
    "yashnabad": (41.288, 69.331),
    "tashkent": (41.311, 69.279),
    # Bukhara
    "buxoro_sh": (39.774, 64.421),
    "buxoro": (39.774, 64.421),
    # Samarkand
    "samarqand_sh": (39.654, 66.959),
    "samarqand": (39.654, 66.959),
}

# Region-level fallback coordinates
REGION_COORDS: dict[str, tuple[float, float]] = {
    "toshkent_shahri": (41.311, 69.279),
    "toshkent": (41.311, 69.279),
    "buxoro": (39.774, 64.421),
    "samarqand": (39.654, 66.959),
    "farg_ona": (40.384, 71.789),
    "andijon": (40.783, 72.344),
    "namangan": (41.000, 71.672),
    "navoiy": (40.103, 65.379),
    "qashqadaryo": (38.860, 65.800),
    "surxondaryo": (37.224, 67.278),
    "jizzax": (40.119, 67.842),
    "sirdaryo": (40.838, 68.665),
    "xorazm": (41.553, 60.631),
    "qoraqalpog_iston": (42.461, 59.600),
}


def resolve_coords(
    district: str | None, region: str | None
) -> tuple[float, float] | None:
    """Resolve coordinates from district first, then region."""
    if district:
        key = district.lower().strip()
        if key in DISTRICT_COORDS:
            return DISTRICT_COORDS[key]
    if region:
        key = region.lower().strip()
        if key in REGION_COORDS:
            return REGION_COORDS[key]
    return None


async def backfill():
    async with async_session_maker() as session:
        # Get all listings without coordinates
        result = await session.execute(
            text(
                "SELECT id, district, region, address FROM listings "
                "WHERE latitude IS NULL OR longitude IS NULL"
            )
        )
        rows = result.fetchall()
        print(f"Found {len(rows)} listings without coordinates")

        updated = 0
        skipped = 0
        for row in rows:
            listing_id, district, region, address = row
            coords = resolve_coords(district, region)
            if coords:
                lat, lng = coords
                await session.execute(
                    text(
                        "UPDATE listings SET latitude = :lat, longitude = :lng WHERE id = :id"
                    ),
                    {"lat": lat, "lng": lng, "id": listing_id},
                )
                updated += 1
                print(
                    f"  ✓ {listing_id} → ({lat}, {lng}) [district={district}, region={region}]"
                )
            else:
                skipped += 1
                print(
                    f"  ✗ {listing_id} — no match [district={district}, region={region}]"
                )

        await session.commit()
        print(f"\nDone: {updated} updated, {skipped} skipped")

        # Verify
        result = await session.execute(
            text(
                "SELECT count(*) FROM listings WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
            )
        )
        print(f"Listings with coordinates: {result.scalar()}")


if __name__ == "__main__":
    asyncio.run(backfill())
