"""Backfill building_type, condition, and land_purpose for all existing listings.

Analyzes description/raw_text using keyword matching to infer values.
Sets sensible defaults when keywords aren't found.

Usage:
    cd backend
    python -m scripts.backfill_building_condition
"""
import asyncio
import re
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.models import Listing, TelegramListing, OLXListing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Keyword patterns ─────────────────────────────────────────────────

NEW_BUILDING_KEYWORDS = re.compile(
    r"новостройк|yangi\s*bino|yangi\s*uy|yangi\s*qurilgan|новый\s*дом|novostr|"
    r"new\s*build|новый\s*жилой|yangi\s*turar",
    re.IGNORECASE,
)

SECONDARY_KEYWORDS = re.compile(
    r"вторичк|вторичное|ikkilamchi|eski\s*bino|old\s*build|б/?у|secondary",
    re.IGNORECASE,
)

EURO_REPAIR_KEYWORDS = re.compile(
    r"евроремонт|еврореп|evro\s*remont|euro\s*remont|euro\s*repair|"
    r"люкс\s*ремонт|lyuks|premium\s*remont|hi.?tech|хай.?тек|"
    r"дизайнерск|авторск|dizayner",
    re.IGNORECASE,
)

COSMETIC_REPAIR_KEYWORDS = re.compile(
    r"косметическ|косметич|kosmetik|средн\w*\s*ремонт|medium.?repair|"
    r"хорош\w*\s*состоян|yaxshi\s*holat|"
    r"обычн\w*\s*ремонт|простой\s*ремонт|oddiy\s*remont|"
    r"свеж\w*\s*ремонт|yangi\s*remont|ta['ʼ]?mir\s*qilingan|отремонтирован",
    re.IGNORECASE,
)

NEEDS_REPAIR_KEYWORDS = re.compile(
    r"требует\s*ремонт|нужен\s*ремонт|ta['ʼ]?mir\s*talab|needs?\s*repair|"
    r"без\s*ремонт|remontga\s*muhtoj|ремонт\s*керак|remont\s*kerak",
    re.IGNORECASE,
)

ROUGH_KEYWORDS = re.compile(
    r"чернов|qora\s*suvoq|black\s*plaster|rough\s*finish|оштукатурен|"
    r"подготовк|под\s*ремонт|tamirga\s*tayyor",
    re.IGNORECASE,
)

LAND_PRIVATE_KEYWORDS = re.compile(
    r"частн\w*\s*строит|xususiy\s*qurilish|ижс|individual|частн\w*\s*дом|"
    r"жилищн\w*\s*строит|uy\s*qurilish|hovli\s*uchun|для\s*дома|"
    r"uy\s*uchun|hovli|участок\s*под\s*дом",
    re.IGNORECASE,
)

LAND_INDUSTRIAL_KEYWORDS = re.compile(
    r"промышлен|sanoat|industrial|коммерч\w*\s*назнач|tijorat\s*maqsad|"
    r"бизнес|biznes|производств|ishlab\s*chiqarish|складск|склад|ombor",
    re.IGNORECASE,
)


def infer_building_type(text: str, property_type: str) -> str:
    """Infer building_type from text. Default: 'secondary' for apartments, 'new' for houses."""
    if not text:
        # Default based on property type
        if property_type in ("apartment", "kvartira"):
            return "secondary"
        return "secondary"

    if NEW_BUILDING_KEYWORDS.search(text):
        return "new"
    if SECONDARY_KEYWORDS.search(text):
        return "secondary"

    # Default
    return "secondary"


def infer_condition(text: str, property_type: str) -> str:
    """Infer condition from text. Default: 'cosmetic'."""
    if not text:
        return "cosmetic"

    if EURO_REPAIR_KEYWORDS.search(text):
        return "euro"
    if ROUGH_KEYWORDS.search(text):
        return "rough"
    if NEEDS_REPAIR_KEYWORDS.search(text):
        return "needs_repair"
    if COSMETIC_REPAIR_KEYWORDS.search(text):
        return "cosmetic"

    return "cosmetic"


def infer_land_purpose(text: str) -> str:
    """Infer land_purpose from text. Default: 'private'."""
    if not text:
        return "private"

    if LAND_INDUSTRIAL_KEYWORDS.search(text):
        return "industrial"
    if LAND_PRIVATE_KEYWORDS.search(text):
        return "private"

    return "private"


# ── Normalize existing OLX values ────────────────────────────────────

OLX_BUILDING_TYPE_MAP = {
    "panel": "secondary",
    "brick": "secondary",
    "monolith": "new",
    "monolithic": "new",
    "block": "secondary",
    "new": "new",
    "new_building": "new",
    "secondary": "secondary",
    "old": "secondary",
}

OLX_CONDITION_MAP = {
    "евроремонт": "euro",
    "euro": "euro",
    "авторский проект": "euro",
    "medium_repair": "cosmetic",
    "средний ремонт": "cosmetic",
    "косметический": "cosmetic",
    "cosmetic": "cosmetic",
    "без ремонта": "needs_repair",
    "needs_repair": "needs_repair",
    "требует ремонта": "needs_repair",
    "черновая": "rough",
    "rough": "rough",
}


def normalize_olx_building_type(val: str | None, text: str, prop_type: str) -> str:
    if val:
        mapped = OLX_BUILDING_TYPE_MAP.get(val.lower().strip())
        if mapped:
            return mapped
    return infer_building_type(text, prop_type)


def normalize_olx_condition(val: str | None, text: str, prop_type: str) -> str:
    if val:
        mapped = OLX_CONDITION_MAP.get(val.lower().strip())
        if mapped:
            return mapped
    return infer_condition(text, prop_type)


# ── Main backfill ────────────────────────────────────────────────────

async def backfill():
    engine = create_async_engine(settings.async_database_url, pool_size=5)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with factory() as db:
        # ── Main Listings ──
        res = await db.execute(select(Listing))
        listings = res.scalars().all()
        main_count = 0
        for listing in listings:
            text = (listing.description or "") + " " + (listing.raw_text or "")
            prop_type = listing.property_type.value if hasattr(listing.property_type, 'value') else str(listing.property_type)

            listing.building_type = infer_building_type(text, prop_type)
            listing.condition = infer_condition(text, prop_type)

            if prop_type == "land":
                listing.land_purpose = infer_land_purpose(text)
            else:
                listing.land_purpose = None

            main_count += 1
        await db.commit()
        logger.info(f"Updated {main_count} main listings")

        # ── Telegram Listings ──
        res = await db.execute(select(TelegramListing))
        listings = res.scalars().all()
        tg_count = 0
        for listing in listings:
            text = (listing.description or "") + " " + (listing.raw_text or "")
            prop_type = listing.property_type or ""

            listing.building_type = infer_building_type(text, prop_type)
            listing.condition = infer_condition(text, prop_type)

            if prop_type == "land":
                listing.land_purpose = infer_land_purpose(text)
            else:
                listing.land_purpose = None

            tg_count += 1
        await db.commit()
        logger.info(f"Updated {tg_count} telegram listings")

        # ── OLX Listings ──
        res = await db.execute(select(OLXListing))
        listings = res.scalars().all()
        olx_count = 0
        for listing in listings:
            text = (listing.description or "") + " " + (listing.raw_text or "")
            prop_type = listing.property_type or ""

            listing.building_type = normalize_olx_building_type(
                listing.building_type, text, prop_type
            )
            listing.condition = normalize_olx_condition(
                listing.condition, text, prop_type
            )

            if prop_type == "land":
                listing.land_purpose = infer_land_purpose(text)
            else:
                listing.land_purpose = None

            olx_count += 1
        await db.commit()
        logger.info(f"Updated {olx_count} OLX listings")

    await engine.dispose()
    logger.info(f"Backfill complete: {main_count + tg_count + olx_count} total listings updated")


if __name__ == "__main__":
    asyncio.run(backfill())
