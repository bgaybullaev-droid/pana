"""Celery tasks for translating listing content between RU and UZ."""

import asyncio
import json
import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import Listing, OLXListing, TelegramListing
from app.services.translation_llm import call_translation_llm
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _get_session():
    """Create a fresh async engine + session for each task invocation.

    This avoids event-loop mismatch errors when asyncio.run() creates a new loop
    while the global engine is bound to a previous (now-closed) loop.
    """
    engine = create_async_engine(
        settings.async_database_url, pool_pre_ping=True, pool_size=2
    )
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
    await engine.dispose()


# Translation prompt template
_TRANSLATE_PROMPT = (
    "Translate the following real estate listing fields from {source_lang} to {target_lang}.\n"
    "Preserve proper nouns, landmark names, district names, street names, metro stations, "
    "measurements (m², sotka), and phone numbers exactly as-is.\n"
    "Return ONLY valid JSON with these keys (omit key if input is empty/null):\n"
    '{{"description": "...", "address": "..."}}\n\n'
    "Input:\n"
    "description: {description}\n"
    "address: {address}"
)

_LANG_NAMES = {"ru": "Russian", "uz": "Uzbek", "en": "English"}

# Uzbek-specific Cyrillic characters (not present in Russian)
_UZ_CYRILLIC = set("ҳғқўҲҒҚЎ")

# Common Uzbek Latin words that distinguish from English
_UZ_LATIN_MARKERS = {
    "xona",
    "xonadon",
    "kvartira",
    "uy",
    "sotix",
    "qavatda",
    "qavat",
    "mebel",
    "jihozlar",
    "hammom",
    "oshxona",
    "balkon",
    "temir",
    "yangi",
    "qurilish",
    "ta'mir",
    "ijaraga",
    "sotiladi",
    "narx",
    "ko'cha",
    "tuman",
    "shahar",
    "viloyat",
    "mahalla",
    "koladi",
    "bor",
    "uchun",
    "bilan",
}

# Batch size for periodic scan
_BATCH_SIZE = 50


def _detect_language(text: str) -> str:
    """Detect language from text using character-set heuristic."""
    if not text:
        return "ru"
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    total = cyrillic + latin
    if total == 0:
        return "ru"
    if cyrillic > 0 and any(ch in _UZ_CYRILLIC for ch in text):
        return "uz"
    if latin > 0:
        words = set(re.findall(r"[a-zA-Z']+", text.lower()))
        uz_hits = words & _UZ_LATIN_MARKERS
        if len(uz_hits) >= 2:
            return "uz"
    if cyrillic / total > 0.5:
        return "ru"
    return "en"


def _get_target_languages(lang: str) -> List[str]:
    """Return target languages to translate into based on source language."""
    if lang == "ru":
        return ["uz"]
    elif lang == "uz":
        return ["ru"]
    else:
        return ["ru", "uz"]


async def _translate_single(table_model, listing_id: str) -> bool:
    """Translate a single listing. Returns True on success."""
    async with _get_session() as db:
        result = await db.execute(
            select(table_model).where(table_model.id == listing_id)
        )
        listing = result.scalar_one_or_none()
        if not listing:
            logger.warning(
                f"[TRANSLATE] Listing {listing_id} not found in {table_model.__tablename__}"
            )
            return False

        if listing.translation_status not in ("pending", "translating"):
            return False

        description = listing.description or ""
        address = listing.address or ""
        lang = (
            _detect_language(description)
            if description
            else (listing.original_language or "ru")
        )

        if lang != listing.original_language:
            logger.info(
                f"[TRANSLATE] {listing_id}: re-detected language {listing.original_language}→{lang}"
            )
            listing.original_language = lang
            if description:
                setattr(listing, f"description_{lang}", description)
            if address:
                setattr(listing, f"address_{lang}", address)

        if not description and not address:
            listing.translation_status = "skipped"
            await db.commit()
            return True

        targets = _get_target_languages(lang)

        listing.translation_status = "translating"
        await db.commit()

        try:
            for target in targets:
                existing = getattr(listing, f"description_{target}", None)
                if existing:
                    continue

                prompt = _TRANSLATE_PROMPT.format(
                    source_lang=_LANG_NAMES[lang],
                    target_lang=_LANG_NAMES[target],
                    description=description,
                    address=address,
                )
                translated = call_translation_llm(prompt)

                if translated.get("description"):
                    setattr(listing, f"description_{target}", translated["description"])
                if translated.get("address"):
                    setattr(listing, f"address_{target}", translated["address"])

                if hasattr(listing, "title_ru") and translated.get("description"):
                    setattr(listing, f"title_{target}", translated["description"][:200])

            listing.translation_status = "completed"
            listing.translated_at = datetime.utcnow()
            await db.commit()
            logger.info(
                f"[TRANSLATE] {table_model.__tablename__} {listing_id}: {lang}→{','.join(targets)} done"
            )
            return True

        except json.JSONDecodeError as e:
            logger.error(f"[TRANSLATE] Invalid JSON from LLM for {listing_id}: {e}")
            listing.translation_status = "failed"
            await db.commit()
            return False
        except Exception as e:
            logger.error(f"[TRANSLATE] Failed for {listing_id}: {e}")
            listing.translation_status = "failed"
            await db.commit()
            return False


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    name="app.workers.tasks.translation.translate_listing",
)
def translate_listing(self, table_name: str, listing_id: str):
    """Translate a single listing's content to the other language.

    Args:
        table_name: 'telegram_listings', 'olx_listings', or 'listings'
        listing_id: UUID of the listing
    """
    model_map = {
        "telegram_listings": TelegramListing,
        "olx_listings": OLXListing,
        "listings": Listing,
    }
    model = model_map.get(table_name)
    if not model:
        logger.error(f"[TRANSLATE] Unknown table: {table_name}")
        return {"success": False, "error": f"Unknown table: {table_name}"}

    try:
        success = asyncio.run(_translate_single(model, listing_id))
        return {"success": success, "table": table_name, "listing_id": listing_id}
    except Exception as exc:
        logger.error(f"[TRANSLATE] Task error for {table_name}/{listing_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(name="app.workers.tasks.translation.translate_pending_listings")
def translate_pending_listings():
    """Periodic task: find pending listings and dispatch translation tasks."""

    async def _scan():
        dispatched = 0
        async with _get_session() as db:
            for model in (TelegramListing, OLXListing, Listing):
                result = await db.execute(
                    select(model.id)
                    .where(model.translation_status == "pending")
                    .limit(_BATCH_SIZE)
                )
                ids = [str(row[0]) for row in result.all()]
                for lid in ids:
                    translate_listing.delay(model.__tablename__, lid)
                    dispatched += 1
                if ids:
                    logger.info(
                        f"[TRANSLATE] Dispatched {len(ids)} from {model.__tablename__}"
                    )
        return dispatched

    total = asyncio.run(_scan())
    return {"dispatched": total}
