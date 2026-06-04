"""F1 — AI listing-description generation (Block A V2.0).

Per V2.0, the parser captures structured parameters + raw source text;
this task generates the user-visible description in three locales (ru,
uz Latin, uz Cyrillic) using OpenAI. The output populates
``Listing.ai_description_{ru,uz,uz_cyrl}``; the listing's status flips
``PENDING_GENERATION`` → ``ACTIVE`` (success) or ``GENERATION_FAILED``
(permanent failure with a structured-params template fallback).

Triggers:
- After parser import (``crawler_import.py``) when the listing has
  ``status=PENDING_GENERATION``.
- After a master-record edit when one of the meaningful parameters
  changed (handled by the listings update endpoint).

Failure modes:
- ``OPENAI_API_KEY`` empty → use the template fallback path; mark
  ``GENERATION_FAILED`` so retries don't waste budget.
- Transient OpenAI error → Celery retries with exponential backoff up
  to 3 times.
- Non-retryable error / hit retry ceiling → set
  ``GENERATION_FAILED`` + populate template description.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from time import perf_counter
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.listing_i18n import (
    localize_deal_type,
    localize_district,
    localize_property_type,
    localize_region,
)
from app.db.models import Listing, ListingStatus
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


# ── prompt construction ──────────────────────────────────────────────

# Block F F5 — Block A's 2000-char limit kept as outer ceiling; F1
# applies a tighter 1500-char head+tail truncation BEFORE this so the
# prompt body never balloons under unusual raw_text bursts.
_RAW_TEXT_MAX_CHARS = 2000

# Block F F1 — head + tail truncation budget for raw_text BEFORE it
# enters the LLM prompt. Aim: 1500 chars of payload, head-then-tail
# so we keep both "what the listing is" and "what the seller
# emphasised at the end" (e.g. price negotiation notes).
_F1_RAW_TEXT_BUDGET_CHARS = 1500
_F1_HEAD_TAIL_CHARS = 700  # head + " […] " + tail, total ≈ 1404 chars

# Block F F1 — PII scrubber regexes. Phones cover Uzbek country code
# variants (+998, 998-, plain 9 digits when surrounded by punctuation).
# We deliberately err on the side of over-scrubbing; the prompt only
# needs context, not the raw phone number (which lives in structured
# Seller fields anyway).
_PII_PHONE_RE = re.compile(r"\+?9?98[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")
_PII_PHONE_BARE_RE = re.compile(r"(?<!\d)\d{9}(?!\d)")
_PII_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

_LANGUAGE_INSTRUCTION = {
    "ru": "Russian (Cyrillic)",
    "uz": "Uzbek written in the Latin script",
    "uz_cyrl": "Uzbek written in the Cyrillic script",
}


def _enum_value(v: Any) -> Any:
    """Unwrap a SQLAlchemy/py enum to its raw string value."""
    return v.value if hasattr(v, "value") else v


def _params_block(listing: Listing) -> str:
    """Render a compact bullet list of structured parameters for the prompt.

    Block F F1 — text-valued parameters (property/deal type, district,
    region) are stored as canonical Latin keys (e.g. ``olmazor``). We
    localize them to all three output locales here so the model writes the
    correct language/script per locale instead of echoing the raw key in,
    say, the Russian copy. Numeric/locale-neutral fields pass through as-is.
    """

    def _trilingual(label: str, fn, key) -> str:
        return (
            f'- {label}: ru="{fn(key, "ru")}" | '
            f'uz="{fn(key, "uz")}" | uz_cyrl="{fn(key, "uz_cyrl")}"'
        )

    pieces = []
    if listing.property_type:
        pieces.append(
            _trilingual("property_type", localize_property_type, _enum_value(listing.property_type))
        )
    if listing.type:
        pieces.append(_trilingual("deal_type", localize_deal_type, _enum_value(listing.type)))
    if listing.rooms is not None:
        pieces.append(f"- rooms: {listing.rooms}")
    if listing.area is not None:
        pieces.append(f"- area_sqm: {listing.area}")
    if listing.floor is not None and listing.total_floors is not None:
        pieces.append(f"- floor: {listing.floor}/{listing.total_floors}")
    elif listing.floor is not None:
        pieces.append(f"- floor: {listing.floor}")
    if listing.district:
        pieces.append(_trilingual("district", localize_district, listing.district))
    if listing.region:
        pieces.append(_trilingual("region", localize_region, listing.region))
    if listing.price:
        pieces.append(f"- price: {listing.price} {_enum_value(listing.currency)}")
    return "\n".join(pieces)


def _scrub_pii(text: str) -> tuple[str, int, int]:
    """Block F F1 — strip phone numbers and emails before prompt build.

    Returns ``(scrubbed, phones_removed, emails_removed)``. The
    structured Seller / Listing fields carry the real phone/email; we
    don't want the LLM seeing them and re-emitting them in the
    generated description.
    """
    if not text:
        return "", 0, 0
    phones_removed = 0
    out, n1 = _PII_PHONE_RE.subn("[contact]", text)
    phones_removed += n1
    out, n2 = _PII_PHONE_BARE_RE.subn("[contact]", out)
    phones_removed += n2
    out, n_email = _PII_EMAIL_RE.subn("[contact]", out)
    return out, phones_removed, n_email


def _truncate_raw_text(text: str, budget: int = _F1_RAW_TEXT_BUDGET_CHARS) -> str:
    """Block F F1 — head + tail truncation to keep prompts predictable.

    Below budget → verbatim. Above → head + " […] " + tail.
    """
    if not text:
        return ""
    if len(text) <= budget:
        return text
    head = text[:_F1_HEAD_TAIL_CHARS].rstrip()
    tail = text[-_F1_HEAD_TAIL_CHARS:].lstrip()
    return f"{head}\n[…]\n{tail}"


def _build_prompt(listing: Listing, *, template_body: Optional[str] = None) -> str:
    """Build a single-shot prompt that asks for all three locales at once.

    Block F F5: when ``template_body`` is supplied (loaded from the
    DB-stored ``prompt_templates`` via the registry), the placeholders
    ``{params_block}`` and ``{raw_text}`` are substituted into the
    template. When ``template_body`` is None we fall back to the
    historical hard-coded prompt — keeps the worker resilient when
    the seed row is missing.

    Returns a string the model is expected to answer with strict JSON of
    ``{"ru": "...", "uz": "...", "uz_cyrl": "..."}``.
    """
    # Block F F1: scrub PII then truncate.
    raw_scrubbed, phones, emails = _scrub_pii(listing.raw_text or "")
    if phones or emails:
        logger.info(
            "ai_generation.pii_scrubbed listing=%s phones=%d emails=%d",
            listing.id,
            phones,
            emails,
        )
    raw = _truncate_raw_text(raw_scrubbed)
    params = _params_block(listing)

    if template_body is not None:
        # DB-stored prompt: do narrow placeholder substitution only.
        # We deliberately use ``str.replace`` not ``.format`` so braces
        # inside the prompt body (e.g. JSON examples) don't trip a
        # KeyError.
        return (
            template_body.replace("{params_block}", params).replace(
                "{raw_text}", raw
            )
        )

    # Hard-coded fallback — preserved verbatim from the historical
    # implementation. Used only when the prompt_templates row is
    # missing (e.g. fresh deployment before seeding).
    return (
        "You are a real-estate copywriter for UcharMarket (Tashkent, Uzbekistan).\n"
        "Write a clean, professional 2–4 sentence listing description for a buyer feed.\n"
        "Rules:\n"
        "- Tone: factual, calm, professional. No exclamation marks. No CAPS.\n"
        "- No phone numbers, no agent name, no calls-to-action.\n"
        "- Do not invent facts. If a parameter is missing, omit it instead of guessing.\n"
        "- 350 characters max per locale.\n"
        "- Output STRICT JSON: {\"ru\":\"…\",\"uz\":\"…\",\"uz_cyrl\":\"…\"}.\n"
        "  ru = Russian (Cyrillic). uz = Uzbek Latin. uz_cyrl = Uzbek Cyrillic.\n"
        "  No markdown, no surrounding prose, just JSON.\n"
        "\n"
        "Structured parameters:\n"
        f"{params}\n"
        "\n"
        "Original source text from realtor (use as context, do NOT copy verbatim):\n"
        f"{raw}\n"
    )


def _template_fallback(listing: Listing, lang: str) -> str:
    """Best-effort description from structured params only (localized).

    Used when F1 generation fails permanently. Every text-valued param is
    localized to ``lang`` (ru / uz / uz_cyrl) via the listing_i18n mirror,
    so the fallback never leaks a raw storage key like "olmazor" into the
    Russian copy. Reads e.g. "1-комн. квартира, Алмазарский р-н, 40 м²".
    """
    rooms_suffix = {"ru": "-комн.", "uz": " xonali", "uz_cyrl": " хонали"}

    lead_bits = []
    if listing.rooms:
        lead_bits.append(f"{listing.rooms}{rooms_suffix[lang]}")
    pt_name = localize_property_type(_enum_value(listing.property_type), lang)
    if pt_name:
        # Lowercase the type so it reads naturally mid-phrase; district
        # stays as-is (it's a proper place name).
        lead_bits.append(pt_name.lower())

    segments = []
    lead = " ".join(lead_bits).strip()
    if lead:
        segments.append(lead)
    if listing.district:
        segments.append(localize_district(listing.district, lang))
    if listing.area:
        unit = "м²" if lang == "ru" else "m²"
        segments.append(f"{int(listing.area)} {unit}")

    if not segments:
        return {
            "ru": "Объявление о недвижимости.",
            "uz": "Ko'chmas mulk e'loni.",
            "uz_cyrl": "Кўчмас мулк эълони.",
        }[lang]
    return ", ".join(segments)


# ── OpenAI call ───────────────────────────────────────────────────────


async def _call_openai(
    prompt: str, *, model: str = "gpt-4o-mini"
) -> Optional[Dict[str, str]]:
    """Call OpenAI; return ``{"ru","uz","uz_cyrl"}`` on success, None on
    parse / API failure. Caller decides whether to retry or fall back.

    Block F F5 — ``model`` is taken from the active prompt template's
    ``model_hint`` (or default gpt-4o-mini) so admin can swap models
    without a code deploy.
    """
    api_key = settings.openai_api_key
    if not api_key:
        logger.warning("OPENAI_API_KEY missing — skipping AI generation.")
        return None
    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.error("openai package missing — install backend/requirements.txt")
        return None

    client = AsyncOpenAI(api_key=api_key)
    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_tokens=600,
        )
    except Exception as e:  # noqa: BLE001 — surfaced via logs
        logger.warning("OpenAI request failed: %s", e)
        raise

    content = (resp.choices[0].message.content or "").strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        logger.warning("OpenAI returned non-JSON: %s", content[:200])
        return None

    if not all(k in data and isinstance(data[k], str) for k in ("ru", "uz", "uz_cyrl")):
        logger.warning("OpenAI JSON missing required keys: %s", list(data.keys()))
        return None
    return {k: data[k].strip() for k in ("ru", "uz", "uz_cyrl")}


# ── Celery entry point ────────────────────────────────────────────────


async def _write_fallback_on_failure(listing_id: str) -> None:
    """Write template fallback to DB when all AI retries are exhausted.

    Called from the on_failure hook so the frontend poll always gets a
    non-null ai_description_ru instead of hanging forever on null.
    """
    from app.db.session import async_session_factory

    try:
        async with async_session_factory() as db:
            row = await db.execute(
                select(Listing).where(Listing.id == UUID(listing_id))
            )
            listing = row.scalar_one_or_none()
            if listing and not listing.ai_description_ru:
                listing.ai_description_ru = _template_fallback(listing, "ru")
                listing.ai_description_uz = _template_fallback(listing, "uz")
                listing.ai_description_uz_cyrl = _template_fallback(listing, "uz_cyrl")
                await db.commit()
                logger.info(
                    "ai_generation.fallback_written listing=%s (on_failure)", listing_id
                )
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "ai_generation.fallback_write_failed listing=%s: %s", listing_id, e
        )


class _GenerateDescriptionTask(celery_app.Task):
    """Custom Task base that writes the template fallback when all retries
    are exhausted, ensuring ai_description_ru is never permanently null."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):  # noqa: ARG002
        listing_id = (args[0] if args else None) or kwargs.get("listing_id")
        if listing_id:
            try:
                asyncio.run(_write_fallback_on_failure(str(listing_id)))
            except Exception as e:  # noqa: BLE001
                logger.warning("ai_generation.on_failure_hook_error: %s", e)


@celery_app.task(
    bind=True,
    base=_GenerateDescriptionTask,
    name="app.workers.tasks.ai_generation.generate_listing_description",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
)
def generate_listing_description(
    self, listing_id: str, triggered_by: str = "auto_parser"
) -> Dict[str, Any]:
    """Sync entry; dispatches to the async coroutine via asyncio.run.

    ``triggered_by`` (Block F F5) is logged into ``ai_generations``:
        auto_parser    — A7 crawler-import flow (default)
        manual         — F1 Stage 1 "Сгенерировать объявление"
        param_change   — F1 Stage 2 regenerate after param drift
        manual_retry   — admin/seller-initiated re-gen of an existing listing
    """
    return asyncio.run(_run(self, listing_id, triggered_by))


async def _run(task, listing_id: str, triggered_by: str) -> Dict[str, Any]:
    from app.db.session import async_session_factory  # local import: cycle
    from app.services.prompt_registry import (
        PromptNotConfigured,
        get_active_prompt,
        record_generation,
    )

    async with async_session_factory() as db:
        listing = await db.execute(
            select(Listing).where(Listing.id == UUID(listing_id))
        )
        listing = listing.scalar_one_or_none()
        if listing is None:
            return {"status": "missing"}

        # Idempotency: if a successful generation already exists, no-op.
        # Block F F1 carve-out: DRAFT regen MUST proceed even if the
        # listing already has AI text (seller is iterating).
        if (
            listing.status == ListingStatus.ACTIVE
            and listing.ai_description_ru
            and triggered_by == "auto_parser"
        ):
            return {"status": "already_generated"}

        # Block F F1 — sellers in the cabinet keep their listing in
        # DRAFT through generation. The worker writes ai_description_*
        # but never flips the status. The seller flips DRAFT → ACTIVE
        # manually after reviewing the text on Stage 2; that PATCH
        # fires the existing autopost + saved-search hooks.
        is_draft_flow = listing.status == ListingStatus.DRAFT

        # UNCONFIRMED short-circuit per A7 V2.0.
        # Drafts created via Stage 1 must have type/price/district before
        # the endpoint accepts them, so this branch only triggers for
        # parser-imported listings.
        if not (listing.type and listing.price and listing.district):
            if not is_draft_flow:
                listing.status = ListingStatus.UNCONFIRMED
                await db.commit()
            return {"status": "unconfirmed"}

        listing.ai_generation_attempted_at = datetime.utcnow()

        # Block F F5: read prompt template from DB; fall back to
        # hard-coded body if registry is empty (resilient to seed gaps).
        active_template = None
        try:
            active_template = await get_active_prompt(db, kind="listing_description")
        except PromptNotConfigured:
            logger.warning(
                "ai_generation.prompt_not_configured listing=%s — using inline fallback",
                listing.id,
            )

        prompt = _build_prompt(
            listing,
            template_body=active_template.body if active_template else None,
        )
        model = (active_template.model_hint if active_template else None) or "gpt-4o-mini"

        # Time the call so we can log duration_ms regardless of outcome.
        started = perf_counter()
        try:
            result = await _call_openai(prompt, model=model)
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            # Best-effort: log the failure outcome before retry.
            try:
                await record_generation(
                    db,
                    model=model,
                    prompt_text=prompt,
                    response_text=f"<exception> {type(exc).__name__}: {exc}"[:4000],
                    duration_ms=duration_ms,
                    outcome="rate_limit"
                    if "rate" in str(exc).lower()
                    else "timeout",
                    triggered_by=triggered_by,
                    listing_id=listing.id,
                    prompt_template_id=active_template.id if active_template else None,
                )
                await db.commit()
            except Exception:
                await db.rollback()
            raise task.retry()  # honored by autoretry_for + max_retries

        duration_ms = int((perf_counter() - started) * 1000)

        if result is None:
            # No API key, JSON parse error, or missing keys → use the
            # structured-params template as a fallback. For DRAFT flow,
            # we still keep the status DRAFT so the seller can see the
            # text and either accept it or hit Regenerate. For the
            # historical PENDING_GENERATION flow we mark GENERATION_FAILED.
            listing.ai_description_ru = _template_fallback(listing, "ru")
            listing.ai_description_uz = _template_fallback(listing, "uz")
            listing.ai_description_uz_cyrl = _template_fallback(listing, "uz_cyrl")
            if not is_draft_flow:
                listing.status = ListingStatus.GENERATION_FAILED
            try:
                await record_generation(
                    db,
                    model=model,
                    prompt_text=prompt,
                    response_text="<no_result>",
                    duration_ms=duration_ms,
                    outcome="invalid_response"
                    if settings.openai_api_key
                    else "fallback_template",
                    triggered_by=triggered_by,
                    listing_id=listing.id,
                    prompt_template_id=active_template.id if active_template else None,
                )
            except Exception:
                logger.warning("ai_generation.record_failed", exc_info=True)
            await db.commit()
            if not is_draft_flow:
                # Notifications + autopost only fire for the historical
                # crawler-import path. DRAFT flips to ACTIVE later via
                # the seller's PATCH, which re-fires these hooks.
                await _notify_sellers_after_generation(db, listing.id)
            return {"status": "fallback_template"}

        listing.ai_description_ru = result["ru"]
        listing.ai_description_uz = result["uz"]
        listing.ai_description_uz_cyrl = result["uz_cyrl"]
        if not is_draft_flow:
            listing.status = ListingStatus.ACTIVE
        # Block F F1 — snapshot params at successful generation so
        # cabinet Stage 2 can detect drift.
        listing.last_ai_param_snapshot = {
            "type": listing.type.value if hasattr(listing.type, "value") else str(listing.type),
            "district": listing.district,
            "price": listing.price,
            "area": float(listing.area) if listing.area is not None else None,
            "rooms": listing.rooms,
        }
        try:
            await record_generation(
                db,
                model=model,
                prompt_text=prompt,
                response_text=json.dumps(result, ensure_ascii=False),
                duration_ms=duration_ms,
                outcome="ok",
                triggered_by=triggered_by,
                listing_id=listing.id,
                prompt_template_id=active_template.id if active_template else None,
            )
        except Exception:
            logger.warning("ai_generation.record_failed", exc_info=True)
        await db.commit()

        if not is_draft_flow:
            # Trigger A4 push fanout — see notify_sellers_of_crawled_listing.
            await _notify_sellers_after_generation(db, listing.id)
            # Block D D4 — newly-active listings with AI text should also
            # be published to the seller's connected channel (if any).
            # DRAFT path defers this — seller's PATCH DRAFT→ACTIVE fires
            # the autopost hook (`_dispatch_autopost_for_status_change`)
            # exactly once.
            await _enqueue_autopost(db, listing.id)
        return {"status": "ok"}


async def _notify_sellers_after_generation(db: AsyncSession, listing_id: UUID) -> None:
    """Hand off to the A4 notification task once generation finishes.

    Defined here as a thin shim so the import is local to the success
    path and we don't take a hard dependency at module-load time.
    """
    try:
        from app.workers.tasks.notifications import (
            notify_sellers_of_crawled_listing,
        )

        notify_sellers_of_crawled_listing.delay(str(listing_id))
    except Exception as e:  # noqa: BLE001
        logger.warning("Skipped A4 fanout for %s: %s", listing_id, e)


async def _enqueue_autopost(db: AsyncSession, listing_id: UUID) -> None:
    """Block D D4 — fire-and-forget autopost task for a freshly ACTIVE
    listing. Reads the seller's autopost binding inline; bails if not
    connected. Publish task is idempotent (uq on (listing_id, channel_id)).
    """
    from app.db.models import Seller

    try:
        listing = (
            await db.execute(select(Listing).where(Listing.id == listing_id))
        ).scalar_one_or_none()
        if listing is None or listing.seller_id is None:
            return
        seller = (
            await db.execute(select(Seller).where(Seller.id == listing.seller_id))
        ).scalar_one_or_none()
        if seller is None:
            return
        if not seller.autopost_enabled or not seller.autopost_channel_id:
            return
        if seller.autopost_verified_at is None:
            return
        from app.workers.tasks.autopost import publish_listing_to_channel

        publish_listing_to_channel.delay(str(listing_id), str(seller.id))
    except Exception as e:  # noqa: BLE001
        logger.warning("Skipped autopost enqueue for %s: %s", listing_id, e)
