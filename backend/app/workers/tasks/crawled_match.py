"""A4 — Crawled-match notification fanout (Block A V2.0).

When F1 finishes generating an AI description for a parser-imported
listing, this task looks up registered sellers whose phone matches and
fires a Telegram push (with inline "Это моё" / "Не моё" buttons) plus an
in-app Notification row. Per-(seller × listing × type) idempotency is
enforced by the unique partial index added in migration
``20260429_prg_view_event_anon_and_status``.

Group-batching (Block A V2.0, A4 push-debounce):
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When the parser imports a burst of crawled listings for the same
seller, sending one Telegram push per match would spam the user.
``notify_sellers_of_crawled_listing`` therefore stages a per-seller
debounce window in Redis (``crawled_match:pending:<seller_id>`` list,
60-second TTL) and schedules
:func:`flush_pending_crawled_pushes` with ``countdown=60`` on the
first hit. When the window closes, the flush task pulls whatever has
accumulated and sends a single consolidated push (a per-listing push
when only one row matched, an "N matches → Open Found" CTA when many).
The in-app ``Notification`` rows are still written immediately per
listing — only the Telegram side is debounced.

Bot-blocked: ``TelegramForbiddenError`` is logged; the DB
``Notification`` row is *always* created first so /found and the
in-app notification list keep their copy.

Expiry: two tasks exist for historical reasons:
* :func:`expire_old_notifications` (legacy, kept for backward compat)
  walks ``expires_at``-based rows.
* :func:`expire_stale_crawled_matches` (current) flips ``read=True``
  on every ``CRAWLED_MATCH`` row older than 7 days that the seller
  never acted on, regardless of whether ``expires_at`` was populated.
  Runs daily at 03:00 via the Celery beat schedule to avoid contention
  with the 04:xx maintenance band.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select

from app.core.config import settings
from app.db.models import (
    Listing,
    ListingStatus,
    Notification,
    NotificationType,
    User,
    UserRole,
)
from app.utils.phone import normalize_phone
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


_BATCH_WINDOW_SEC = 60  # 1 min debounce, per A4 spec
_NOTIFICATION_TTL_DAYS = 7

# Redis keys: ``crawled_match:pending:<seller_id>``  -> LIST of listing UUIDs.
# Companion ``crawled_match:scheduled:<seller_id>`` -> "1" with TTL while a
# flush is pending so we don't double-schedule.
_REDIS_PENDING_KEY = "crawled_match:pending:{seller_id}"
_REDIS_SCHEDULED_KEY = "crawled_match:scheduled:{seller_id}"


def _get_sync_redis():
    """Lightweight sync Redis client; debounce is fire-and-forget so we
    don't want the async overhead. Same connection URL the rest of the
    workers package uses."""
    import redis  # local import keeps the module importable even if redis
    # is missing in some constrained test envs.

    return redis.from_url(settings.redis_connection_url, decode_responses=True)


def _seller_lang(user: User) -> str:
    """Best-guess locale for a Telegram-bot template lookup."""
    lang = (getattr(user, "language", None) or "ru").lower()
    if lang.startswith("uz") and "cyr" in lang:
        return "uz_cyrl"
    if lang.startswith("uz"):
        return "uz"
    return "ru"


def _bot_card_text(listing: Listing, lang: str) -> str:
    """Build the Telegram message body using AI text + key params."""
    desc = (
        listing.ai_description_uz_cyrl
        if lang == "uz_cyrl"
        else listing.ai_description_uz
        if lang == "uz"
        else listing.ai_description_ru
    ) or ""
    title_map = {
        "ru": "🏠 Мы нашли ваше новое объявление",
        "uz": "🏠 Yangi e'loningiz topildi",
        "uz_cyrl": "🏠 Янги эълонингиз топилди",
    }
    price_line = f"{int(listing.price)} {listing.currency}" if listing.price else ""
    src_label = listing.source_url or ""
    parts = [
        f"<b>{title_map.get(lang, title_map['ru'])}</b>",
        "",
        desc[:600],
        "",
        f"💵 {price_line}".strip(),
    ]
    if src_label:
        parts.append(f"🔗 {src_label}")
    return "\n".join(p for p in parts if p)


# ── Celery entries ────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.crawled_match.notify_sellers_of_crawled_listing",
)
def notify_sellers_of_crawled_listing(listing_id: str) -> Dict[str, Any]:
    """Look up matching sellers by phone, dispatch push + in-app row.

    Sync entry; the OpenAI integration in ai_generation also calls this.
    """
    return asyncio.run(_run_match(listing_id))


async def _run_match(listing_id: str) -> Dict[str, Any]:
    from app.db.session import async_session_factory

    async with async_session_factory() as db:
        listing = (
            await db.execute(select(Listing).where(Listing.id == UUID(listing_id)))
        ).scalar_one_or_none()
        if listing is None:
            return {"status": "missing"}
        # Skip statuses that should never trigger pushes.
        if listing.status not in (
            ListingStatus.ACTIVE,
            ListingStatus.GENERATION_FAILED,
        ):
            return {"status": "wrong_status", "value": str(listing.status)}
        if listing.seller_id is not None:
            return {"status": "already_claimed"}
        if not listing.phone:
            return {"status": "no_phone"}
        if not (
            listing.ai_description_ru
            or listing.ai_description_uz
            or listing.ai_description_uz_cyrl
        ):
            return {"status": "no_ai_text"}

        suffix = normalize_phone(listing.phone)
        if not suffix or len(suffix) < 9:
            return {"status": "phone_unparseable"}

        # Block C V2.0 (C4) — match against ANY of the user's verified
        # phones (user_phones), not just the auth primary. Uses a JOIN
        # to user_phones; the existing User.phone match is preserved
        # because the backfill ensures every legacy user has a primary
        # row in user_phones too.
        from app.db.models import UserPhone

        sellers = (
            await db.execute(
                select(User)
                .join(UserPhone, UserPhone.user_id == User.id)
                .where(
                    and_(
                        func.right(UserPhone.phone, 9) == suffix[-9:],
                        User.role.in_([UserRole.SELLER, UserRole.ADMIN]),
                        User.deleted_at.is_(None),
                    )
                )
                .distinct()
            )
        ).scalars().all()

        queued = 0
        skipped = 0
        for user in sellers:
            # Idempotency check at row level (DB unique index also enforces).
            existing = (
                await db.execute(
                    select(Notification.id).where(
                        Notification.user_id == user.id,
                        Notification.listing_id == listing.id,
                        Notification.type == NotificationType.CRAWLED_MATCH,
                    )
                )
            ).first()
            if existing:
                skipped += 1
                continue

            lang = _seller_lang(user)
            title_map = {
                "ru": "Мы нашли ваше объявление",
                "uz": "E'loningiz topildi",
                "uz_cyrl": "Эълонингиз топилди",
            }
            body_short = (
                listing.ai_description_uz_cyrl
                if lang == "uz_cyrl"
                else listing.ai_description_uz
                if lang == "uz"
                else listing.ai_description_ru
            ) or ""

            # IMPORTANT: insert the in-app row BEFORE any Telegram side-effect
            # so a bot-blocked seller still gets their /found item visible
            # in the buyer/seller cabinet. The Telegram side is enqueued
            # via Redis debounce + Celery countdown — see flush_pending_crawled_pushes.
            db.add(
                Notification(
                    user_id=user.id,
                    type=NotificationType.CRAWLED_MATCH,
                    title=title_map[lang],
                    message=body_short[:240],
                    listing_id=listing.id,
                    source="crawler",
                    expires_at=datetime.utcnow() + timedelta(days=_NOTIFICATION_TTL_DAYS),
                )
            )
            await db.flush()
            queued += 1

            # Stage Telegram push via Redis debounce — collapses bursts of
            # matches per seller into one consolidated message. Falls back
            # to immediate single-push when Redis is unavailable so we
            # never silently drop the notification.
            if getattr(user, "telegram_id", None):
                if not _enqueue_debounced_push(str(user.id), str(listing.id)):
                    # Redis down: send the per-listing push synchronously.
                    await _send_push(user.telegram_id, listing, lang)

        await db.commit()
        logger.info(
            "crawled-match notify listing=%s queued=%d skipped=%d sellers=%d",
            listing.id,
            queued,
            skipped,
            len(sellers),
        )
        return {
            "status": "ok",
            "queued": queued,
            "skipped": skipped,
            "sellers_matched": len(sellers),
        }


# ── Redis debounce helpers ────────────────────────────────────────────


def _enqueue_debounced_push(seller_id: str, listing_id: str) -> bool:
    """Push the listing id into the per-seller debounce list and, if no
    flush is already scheduled, schedule a Celery countdown task.

    Returns ``True`` on success, ``False`` when Redis is unreachable —
    the caller can then fall back to an immediate per-listing push.
    """
    pending_key = _REDIS_PENDING_KEY.format(seller_id=seller_id)
    scheduled_key = _REDIS_SCHEDULED_KEY.format(seller_id=seller_id)
    try:
        r = _get_sync_redis()
        # Append + set TTL atomically via pipeline.
        with r.pipeline() as pipe:
            pipe.rpush(pending_key, listing_id)
            pipe.expire(pending_key, _BATCH_WINDOW_SEC + 30)
            pipe.execute()
        # SET NX with TTL: only schedule a flush task if one isn't pending.
        first_hit = bool(r.set(scheduled_key, "1", nx=True, ex=_BATCH_WINDOW_SEC + 30))
        if first_hit:
            flush_pending_crawled_pushes.apply_async(
                args=[seller_id], countdown=_BATCH_WINDOW_SEC
            )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("crawled-match debounce enqueue failed (%s); push falls back", exc)
        return False


@celery_app.task(
    name="app.workers.tasks.crawled_match.flush_pending_crawled_pushes",
)
def flush_pending_crawled_pushes(seller_id: str) -> Dict[str, Any]:
    """Consume queued listing ids for a seller and send one consolidated push.

    Single match in the window → per-listing card with claim/reject buttons
    (same shape as the historical immediate path).
    Multiple matches → grouped message with a count and an "Open Found"
    deep-link button, no per-listing buttons (the seller acts inside the
    cabinet at /found).
    """
    return asyncio.run(_flush_pending(seller_id))


async def _flush_pending(seller_id: str) -> Dict[str, Any]:
    pending_key = _REDIS_PENDING_KEY.format(seller_id=seller_id)
    scheduled_key = _REDIS_SCHEDULED_KEY.format(seller_id=seller_id)

    listing_ids: List[str] = []
    try:
        r = _get_sync_redis()
        # Atomically drain.
        with r.pipeline() as pipe:
            pipe.lrange(pending_key, 0, -1)
            pipe.delete(pending_key)
            pipe.delete(scheduled_key)
            results = pipe.execute()
        listing_ids = list(results[0] or [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("crawled-match flush: redis drain failed: %s", exc)
        return {"status": "redis_unavailable", "sent": 0}

    if not listing_ids:
        return {"status": "empty", "sent": 0}

    from app.db.session import async_session_factory

    async with async_session_factory() as db:
        user = (
            await db.execute(select(User).where(User.id == UUID(seller_id)))
        ).scalar_one_or_none()
        if user is None or not getattr(user, "telegram_id", None):
            return {"status": "no_recipient", "sent": 0}

        lang = _seller_lang(user)

        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique_ids: List[str] = []
        for lid in listing_ids:
            if lid not in seen:
                seen.add(lid)
                unique_ids.append(lid)

        if len(unique_ids) == 1:
            listing = (
                await db.execute(
                    select(Listing).where(Listing.id == UUID(unique_ids[0]))
                )
            ).scalar_one_or_none()
            if listing is None:
                return {"status": "missing_listing", "sent": 0}
            ok = await _send_push(user.telegram_id, listing, lang)
            return {"status": "ok", "sent": int(ok), "mode": "single"}

        # Multi: grouped summary push.
        ok = await _send_grouped_push(user.telegram_id, len(unique_ids), lang)
        return {"status": "ok", "sent": int(ok), "mode": "grouped", "count": len(unique_ids)}


async def _send_grouped_push(telegram_id: int, count: int, lang: str) -> bool:
    """Send a single consolidated message when the debounce window
    accumulated multiple matches. CTA opens the seller's /found page."""
    try:
        from aiogram.exceptions import TelegramForbiddenError
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        from app.bot.notifications import get_bot_instance
    except ImportError:
        logger.warning("aiogram or bot module unavailable; skipping grouped push")
        return False

    bot = get_bot_instance()
    if bot is None:
        logger.warning("Bot instance not initialised; skipping grouped push")
        return False

    title_map = {
        "ru": f"🏠 Мы нашли <b>{count}</b> ваших объявлений",
        "uz": f"🏠 <b>{count}</b> ta e'loningiz topildi",
        "uz_cyrl": f"🏠 <b>{count}</b> та эълонингиз топилди",
    }
    cta_label = {
        "ru": "Открыть Found",
        "uz": "Found-ni ochish",
        "uz_cyrl": "Found-ни очиш",
    }[lang]

    web_app_base = getattr(settings, "frontend_base_url", None) or ""
    found_url = (web_app_base.rstrip("/") + "/seller/found") if web_app_base else None
    kb_rows = []
    if found_url:
        kb_rows.append([InlineKeyboardButton(text=cta_label, url=found_url)])
    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows) if kb_rows else None

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=title_map.get(lang, title_map["ru"]),
            parse_mode="HTML",
            reply_markup=kb,
        )
        return True
    except TelegramForbiddenError:
        logger.info("Grouped push to %s skipped: bot blocked", telegram_id)
        return False
    except Exception as exc:  # noqa: BLE001
        logger.info("Grouped push to %s skipped: %s", telegram_id, exc)
        return False


async def _send_push(telegram_id: int, listing: Listing, lang: str) -> bool:
    """Send the inline-keyboard push. Bot-blocked is logged-and-swallowed.

    The corresponding ``Notification`` row is created by the caller
    BEFORE this is invoked, so a ``TelegramForbiddenError`` here never
    means we lose the in-app surface — only the push channel."""
    try:
        from aiogram.exceptions import TelegramForbiddenError
        from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

        from app.bot.notifications import get_bot_instance
    except ImportError:
        logger.warning("aiogram or bot module unavailable; skipping push")
        return False

    bot = get_bot_instance()
    if bot is None:
        logger.warning("Bot instance not initialised; skipping push")
        return False

    claim_label = {
        "ru": "✓ Это моё",
        "uz": "✓ Meniki",
        "uz_cyrl": "✓ Меники",
    }[lang]
    reject_label = {
        "ru": "✗ Не моё",
        "uz": "✗ Meniki emas",
        "uz_cyrl": "✗ Меники эмас",
    }[lang]
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=claim_label, callback_data=f"claim_crawled:{listing.id}"
                ),
                InlineKeyboardButton(
                    text=reject_label, callback_data=f"reject_crawled:{listing.id}"
                ),
            ]
        ]
    )
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=_bot_card_text(listing, lang),
            parse_mode="HTML",
            reply_markup=kb,
        )
        return True
    except TelegramForbiddenError:
        # Seller has blocked the bot. The in-app Notification row was
        # already inserted by the caller, so /found still works.
        logger.info("Bot push to %s skipped: blocked by user", telegram_id)
        return False
    except Exception as e:  # bot blocked, network, etc.
        logger.info("Bot push to %s skipped: %s", telegram_id, e)
        return False


# ── Daily expiry job ──────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.crawled_match.expire_old_notifications",
)
def expire_old_notifications() -> Dict[str, Any]:
    return asyncio.run(_run_expiry())


async def _run_expiry() -> Dict[str, Any]:
    from app.db.session import async_session_factory

    async with async_session_factory() as db:
        rows = (
            await db.execute(
                select(Notification).where(
                    Notification.type == NotificationType.CRAWLED_MATCH,
                    Notification.expires_at.is_not(None),
                    Notification.expires_at <= datetime.utcnow(),
                    Notification.read.is_(False),
                )
            )
        ).scalars().all()

        for n in rows:
            n.read = True  # mark as resolved; UI will surface them on Found via pull
        await db.commit()
        logger.info("crawled-match expiry rolled %d notifications", len(rows))
        return {"expired": len(rows)}


@celery_app.task(
    name="app.workers.tasks.crawled_match.expire_stale_crawled_matches",
)
def expire_stale_crawled_matches() -> Dict[str, Any]:
    """Mark CRAWLED_MATCH notifications stale after 7 days of seller inaction.

    Wider net than :func:`expire_old_notifications`: doesn't require an
    ``expires_at`` value, just checks ``created_at < now() - 7d`` AND
    ``read = False``. Sets ``read=True`` so the bot stops re-surfacing
    these rows in /found pulls and so the unread badge clears.

    Scheduled daily 03:00 Asia/Tashkent — see ``celery_app.beat_schedule``.
    """
    return asyncio.run(_run_stale_expiry())


async def _run_stale_expiry() -> Dict[str, Any]:
    from sqlalchemy import update

    from app.db.session import async_session_factory

    cutoff = datetime.utcnow() - timedelta(days=_NOTIFICATION_TTL_DAYS)
    async with async_session_factory() as db:
        result = await db.execute(
            update(Notification)
            .where(
                Notification.type == NotificationType.CRAWLED_MATCH,
                Notification.created_at < cutoff,
                Notification.read.is_(False),
            )
            .values(read=True)
            .execution_options(synchronize_session=False)
        )
        await db.commit()
        rowcount = getattr(result, "rowcount", 0) or 0
        logger.info("crawled-match stale-expiry marked %d notifications read", rowcount)
        return {"expired": rowcount}
