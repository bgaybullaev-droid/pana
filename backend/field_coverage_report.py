"""Field-coverage report for the listing feed (no LLM, read-only).

Prints, per source table (platform Listing / Telegram / OLX), how many rows
have each filterable field populated. This is the decision input for the
re-parse effort: if `floor` / `area` / `condition` / `building_type` are
sparsely filled on the crawler sources, a `raw_text` re-parse would lift
filter coverage; if they're already dense, it's not worth the LLM spend.

Run on the VPS (where the production DB is reachable), e.g.:

    docker compose run --rm api python field_coverage_report.py

or, inside the backend venv:

    cd backend && source venv/bin/activate && python field_coverage_report.py

The script only issues SELECT … COUNT() queries; it never writes.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import func, select, text  # noqa: E402

# Field → SQL predicate counting a row as "populated" for that field.
# Predicates are evaluated as FILTER clauses on COUNT(), so they reference
# the source table's own columns.
_COMMON_FIELDS = {
    "rooms": "rooms IS NOT NULL",
    "floor": "floor IS NOT NULL",
    "total_floors": "total_floors IS NOT NULL",
    "building_type": "building_type IS NOT NULL",
    "condition": "condition IS NOT NULL",
    "region": "region IS NOT NULL",
    "district": "district IS NOT NULL",
}

# Platform-only deal-terms + photo coverage.
_PLATFORM_EXTRA = {
    "area": "area IS NOT NULL",
    "has_photo": (
        "EXISTS (SELECT 1 FROM listing_images li "
        "WHERE li.listing_id = listings.id)"
    ),
    "furniture": "furniture IS NOT NULL AND furniture <> 'none'",
    "mortgage_ok": "mortgage_ok IS TRUE",
    "installment_ok": "installment_ok IS TRUE",
    "halol_ok": "halol_ok IS TRUE",
    "allowed_pets": "allowed_pets IS TRUE",
    "allowed_students": "allowed_students IS TRUE",
    "utilities_incl": "utilities_incl IS TRUE",
    "rent_period": "rent_period IS NOT NULL",
    "deposit": "deposit IS NOT NULL",
    "deed_type": "deed_type IS NOT NULL",
}

# Crawler tables store area as `area_sqm` and images as a JSONB array.
_CRAWLER_EXTRA = {
    "area_sqm": "area_sqm IS NOT NULL",
    "has_photo": (
        "jsonb_typeof(images) = 'array' AND jsonb_array_length(images) > 0"
    ),
}
_OLX_EXTRA = {**_CRAWLER_EXTRA, "furnishing": "furnishing IS NOT NULL"}


async def _coverage(db, model, fields, where_clause):
    """Return (total, {field: filled_count}) for one source."""
    cols = [func.count().label("total")]
    for label, expr in fields.items():
        cols.append(func.count().filter(text(expr)).label(label))
    q = select(*cols).select_from(model)
    if where_clause is not None:
        q = q.where(where_clause)
    row = (await db.execute(q)).one()._mapping
    total = row["total"]
    filled = {label: row[label] for label in fields}
    return total, filled


def _print_table(title, total, filled):
    print()
    print(f"━━ {title} ━━  (active rows: {total})")
    if total == 0:
        print("   (no rows)")
        return
    width = max(len(k) for k in filled)
    for label, count in filled.items():
        pct = 100.0 * count / total
        bar = "█" * int(pct / 5)
        print(f"   {label:<{width}}  {count:>7} / {total:<7} {pct:5.1f}%  {bar}")


async def main():
    from app.db.database import async_session_maker
    from app.db.models import (
        Listing,
        ListingStatus,
        ModerationStatus,
        OLXListing,
        TelegramListing,
    )

    async with async_session_maker() as db:
        # Platform: mirror the feed's active/approved/visible constraint.
        plat_total, plat_filled = await _coverage(
            db,
            Listing,
            {**_COMMON_FIELDS, **_PLATFORM_EXTRA},
            (Listing.status == ListingStatus.ACTIVE)
            & (Listing.moderation_status == ModerationStatus.APPROVED)
            & (Listing.deleted_at.is_(None)),
        )
        # Telegram: all rows.
        tg_total, tg_filled = await _coverage(
            db, TelegramListing, {**_COMMON_FIELDS, **_CRAWLER_EXTRA}, None
        )
        # OLX: mirror the feed's "not yet claimed/converted" constraint.
        olx_total, olx_filled = await _coverage(
            db,
            OLXListing,
            {**_COMMON_FIELDS, **_OLX_EXTRA},
            OLXListing.converted_listing_id.is_(None),
        )

    print("=" * 64)
    print("LISTING FEED — FIELD COVERAGE REPORT")
    print("=" * 64)
    _print_table("Platform (Listing)", plat_total, plat_filled)
    _print_table("Telegram (TelegramListing)", tg_total, tg_filled)
    _print_table("OLX (OLXListing)", olx_total, olx_filled)

    # Decision hint: wave-1 fields that a re-parse could lift on crawler rows.
    print()
    print("─" * 64)
    print("Re-parse signal — wave-1 fill rate on crawler sources:")
    for label, total, filled in [
        ("Telegram", tg_total, tg_filled),
        ("OLX", olx_total, olx_filled),
    ]:
        if total == 0:
            continue
        parts = []
        for f in ("floor", "condition", "building_type"):
            parts.append(f"{f}={100.0 * filled[f] / total:.0f}%")
        area_key = "area_sqm"
        parts.insert(0, f"area={100.0 * filled[area_key] / total:.0f}%")
        print(f"   {label:<9} {'  '.join(parts)}")
    print(
        "\n   Low % on floor/area/condition → re-parse from raw_text would help."
        "\n   Already high → re-parse not worth the LLM spend."
    )


if __name__ == "__main__":
    asyncio.run(main())
