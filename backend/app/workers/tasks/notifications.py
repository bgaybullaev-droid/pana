"""Notification-related Celery tasks."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

import redis
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from sqlalchemy import delete, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models import (
    Listing,
    ListingStatus,
    ModerationStatus,
    Notification,
    NotificationPreferences,
    NotificationType,
    User,
)
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _get_session():
    """Create a fresh async engine + session for each task invocation."""
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


def _get_sync_redis() -> redis.Redis:
    """Get a sync Redis client for use in Celery tasks."""
    return redis.from_url(settings.redis_connection_url, decode_responses=True)


# ---------------------------------------------------------------------------
# Notification message templates
# ---------------------------------------------------------------------------

_PROPERTY_TYPE_LABELS = {
    "ru": {
        "apartment": "Квартира",
        "house": "Дом",
        "commercial": "Коммерческая",
        "land": "Земельный участок",
    },
    "uz": {
        "apartment": "Kvartira",
        "house": "Uy",
        "commercial": "Tijorat",
        "land": "Yer uchastkasi",
    },
}

_LISTING_TYPE_LABELS = {
    "ru": {"sell": "Продажа", "rent": "Аренда"},
    "uz": {"sell": "Sotish", "rent": "Ijara"},
}

_TITLE_TEMPLATES = {
    "ru": "Новое объявление",
    "uz": "Yangi e'lon",
}

_MESSAGE_TEMPLATES = {
    "ru": "{listing_type}: {property_type}{rooms_text}, {district} — {price}",
    "uz": "{listing_type}: {property_type}{rooms_text}, {district} — {price}",
}

_TELEGRAM_TEMPLATES = {
    "ru": (
        "🏠 <b>Новое объявление по вашим фильтрам!</b>\n\n"
        "{listing_type}: {property_type}{rooms_text}\n"
        "📍 {district}\n"
        "💰 {price}\n\n"
        '👉 <a href="{link}">Открыть объявление</a>'
    ),
    "uz": (
        "🏠 <b>Filtrlaringizga mos yangi e'lon!</b>\n\n"
        "{listing_type}: {property_type}{rooms_text}\n"
        "📍 {district}\n"
        "💰 {price}\n\n"
        '👉 <a href="{link}">E\'lonni ochish</a>'
    ),
}

# Templates for saved-search match notifications (distinguished by 🔍).
_SAVED_SEARCH_TITLE = {
    "ru": "Новое по вашему поиску",
    "uz": "Qidiruvingizga yangi e'lon",
}

_SAVED_SEARCH_MESSAGE = {
    "ru": "Новое по «{search_name}»: {listing_type} {property_type}{rooms_text}, {district} — {price}",
    "uz": "«{search_name}»ga mos: {listing_type} {property_type}{rooms_text}, {district} — {price}",
}

_SAVED_SEARCH_TELEGRAM = {
    "ru": (
        "🔍 <b>Новое по вашему поиску «{search_name}»!</b>\n\n"
        "{listing_type}: {property_type}{rooms_text}\n"
        "📍 {district}\n"
        "💰 {price}\n\n"
        '👉 <a href="{link}">Открыть объявление</a>'
    ),
    "uz": (
        "🔍 <b>«{search_name}» bo'yicha yangi e'lon!</b>\n\n"
        "{listing_type}: {property_type}{rooms_text}\n"
        "📍 {district}\n"
        "💰 {price}\n\n"
        '👉 <a href="{link}">E\'lonni ochish</a>'
    ),
}

_ROOMS_TEXT = {
    "ru": ", {n} комн.",
    "uz": ", {n} xona",
}


def _listing_deep_link(listing_id: str) -> str:
    """Build Telegram Mini App deep link for a listing."""
    bot = settings.telegram_bot_username or "TestUcharBot"
    return f"https://t.me/{bot}?startapp=listing_{listing_id}"


def _build_notification_texts(listing: Listing, lang: str) -> dict:
    """Build title, message, and telegram_message for a listing notification."""
    lang = lang if lang in ("ru", "uz") else "ru"

    property_label = _PROPERTY_TYPE_LABELS[lang].get(
        listing.property_type.value, listing.property_type.value
    )
    listing_type_label = _LISTING_TYPE_LABELS[lang].get(
        listing.type.value, listing.type.value
    )

    rooms_text = ""
    if listing.rooms:
        rooms_text = _ROOMS_TEXT[lang].format(n=listing.rooms)

    district = listing.district or "—"
    currency_symbol = "$" if listing.currency.value == "USD" else "сум"
    price = f"{listing.price:,} {currency_symbol}"

    fmt = dict(
        listing_type=listing_type_label,
        property_type=property_label,
        rooms_text=rooms_text,
        district=district,
        price=price,
    )

    return {
        "title": _TITLE_TEMPLATES[lang],
        "message": _MESSAGE_TEMPLATES[lang].format(**fmt),
        "telegram_message": _TELEGRAM_TEMPLATES[lang].format(**fmt),
    }


# ---------------------------------------------------------------------------
# Price drop templates
# ---------------------------------------------------------------------------

_PRICE_DROP_TITLE = {"ru": "Цена снижена!", "uz": "Narx tushdi!"}

_PRICE_DROP_MESSAGE = {
    "ru": "Цена снижена на {percent}%: {old} → {new}",
    "uz": "Narx {percent}% ga tushdi: {old} → {new}",
}

_PRICE_DROP_TELEGRAM = {
    "ru": '📉 <b>Цена снижена!</b>\n\n{old} → {new} (−{percent}%)\n\n👉 <a href="{link}">Открыть объявление</a>',
    "uz": '📉 <b>Narx tushdi!</b>\n\n{old} → {new} (−{percent}%)\n\n👉 <a href="{link}">E\'lonni ochish</a>',
}


def _build_price_drop_texts(
    lang: str,
    old_price: int,
    new_price: int,
    percent: float,
    currency_symbol: str,
    listing_id: str = "",
) -> dict:
    lang = lang if lang in ("ru", "uz") else "ru"
    fmt = dict(
        old=f"{old_price:,} {currency_symbol}",
        new=f"{new_price:,} {currency_symbol}",
        percent=percent,
        link=_listing_deep_link(listing_id),
    )
    return {
        "title": _PRICE_DROP_TITLE[lang],
        "message": _PRICE_DROP_MESSAGE[lang].format(**fmt),
        "telegram_message": _PRICE_DROP_TELEGRAM[lang].format(**fmt),
    }


# ---------------------------------------------------------------------------
# Comment / favorite notification templates (localized)
# ---------------------------------------------------------------------------

_COMMENT_REPLY_TITLE = {"ru": "Ответ на комментарий", "uz": "Izohga javob"}
_COMMENT_REPLY_MESSAGE = {
    "ru": "{name} ответил на ваш комментарий",
    "uz": "{name} izohingizga javob berdi",
}

_NEW_COMMENT_TITLE = {"ru": "Новый комментарий", "uz": "Yangi izoh"}
_NEW_COMMENT_MESSAGE = {
    "ru": "{name} оставил комментарий к вашему объявлению",
    "uz": "{name} e'loningizga izoh qoldirdi",
}

_FAVORITE_UPDATE_TITLE = {
    "ru": "Новое добавление в избранное",
    "uz": "Sevimlilarga qo'shildi",
}
_FAVORITE_UPDATE_MESSAGE = {
    "ru": "{name} добавил ваше объявление в избранное",
    "uz": "{name} e'loningizni sevimlilarga qo'shdi",
}

_LISTING_APPROVED_TITLE = {"ru": "Объявление одобрено", "uz": "E'lon tasdiqlandi"}
_LISTING_APPROVED_MESSAGE = {
    "ru": "Ваше объявление одобрено и опубликовано",
    "uz": "E'loningiz tasdiqlandi va e'lon qilindi",
}

_LISTING_REJECTED_TITLE = {"ru": "Объявление отклонено", "uz": "E'lon rad etildi"}
_LISTING_REJECTED_MESSAGE = {
    "ru": "Ваше объявление отклонено: {reason}",
    "uz": "E'loningiz rad etildi: {reason}",
}


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _check_and_increment_daily_limit(
    r: redis.Redis,
    user_id,
    daily_limit: int,
    today_str: str,
) -> bool:
    """Check if user is within daily Telegram limit; if so, increment and return True."""
    daily_key = f"notif_daily:{user_id}:{today_str}"
    current_count = r.get(daily_key)
    if current_count is not None and int(current_count) >= daily_limit:
        return False
    pipe = r.pipeline()
    pipe.incr(daily_key)
    pipe.expire(daily_key, 86400)
    pipe.execute()
    return True


def _is_within_time_window(prefs: NotificationPreferences) -> bool:
    """Check if current time in user's timezone is within their notification window."""
    import pytz

    try:
        tz = pytz.timezone(prefs.timezone or "Asia/Tashkent")
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone("Asia/Tashkent")

    now_local = datetime.now(tz).time()
    start = prefs.time_start
    end = prefs.time_end

    if start <= end:
        return start <= now_local <= end
    # Wraps midnight (e.g. 22:00 – 06:00)
    return now_local >= start or now_local <= end


async def _log_prefs_rejections(
    db: "AsyncSession",
    listing_id: str,
    listing_type: str,
    property_type: str,
    district: Optional[str],
    price: Optional[int],
    rooms: Optional[int],
    owner_user_id,
    matched_user_ids: set,
) -> None:
    """Explain why each non-matched user with prefs was filtered out.

    Runs the same conditions the SQL matcher uses, but in Python so we
    can log a specific reason per user. Keeps debugging fast without
    adding cost to the hot path — one extra query per listing.
    """
    NP = NotificationPreferences
    q = (
        select(NP, User)
        .join(User, NP.user_id == User.id)
        .where(User.deleted_at.is_(None))
    )
    if owner_user_id:
        q = q.where(User.id != owner_user_id)
    rows = (await db.execute(q)).all()
    for prefs, user in rows:
        if user.id in matched_user_ids:
            continue
        reason = _explain_prefs_mismatch(
            prefs, listing_type, property_type, district, price, rooms
        )
        logger.info(
            "prefs reject user=%s listing=%s reason=%s",
            user.id,
            listing_id,
            reason,
        )


def _explain_prefs_mismatch(
    prefs: "NotificationPreferences",
    listing_type: str,
    property_type: str,
    district: Optional[str],
    price: Optional[int],
    rooms: Optional[int],
) -> str:
    if prefs.listing_types and listing_type not in prefs.listing_types:
        return f"listing_type_mismatch({listing_type} not in {prefs.listing_types})"
    if prefs.property_types and property_type not in prefs.property_types:
        return f"property_type_mismatch({property_type} not in {prefs.property_types})"
    if district and prefs.districts and district not in prefs.districts:
        return f"district_mismatch({district} not in {prefs.districts})"
    if price is not None:
        if prefs.price_min is not None and price < prefs.price_min:
            return f"price_below_min({price}<{prefs.price_min})"
        if prefs.price_max is not None and price > prefs.price_max:
            return f"price_above_max({price}>{prefs.price_max})"
    if rooms is not None and prefs.rooms and rooms not in prefs.rooms:
        return f"rooms_mismatch({rooms} not in {prefs.rooms})"
    return "unknown"


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_telegram_notification(
    self,
    user_telegram_id: int,
    message: str,
    parse_mode: str = "HTML",
    reply_markup_spec: Optional[list] = None,
) -> Dict[str, Any]:
    """Send a Telegram notification to a user via the bot.

    Block D D2 — ``reply_markup_spec`` is an optional list-of-lists of
    button dicts (as produced by
    ``services.listing_push.build_listing_action_kb_spec``). When
    present, the task reconstructs an ``InlineKeyboardMarkup`` and
    attaches it. Old callers that omit the arg get the original
    text-only behavior — fully backward compatible.

    Failure modes (unchanged):
      - Telegram forbidden → swallowed, returns ``reason="blocked"``.
      - Telegram bad-request → swallowed, returns ``reason="bad_request"``.
      - Other exceptions → Celery retry (up to 3, with 60s delay).
    """
    try:

        async def _send():
            from aiogram.types import (
                InlineKeyboardButton,
                InlineKeyboardMarkup,
            )

            bot = Bot(token=settings.telegram_bot_token)
            try:
                reply_markup = None
                if reply_markup_spec:
                    reply_markup = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(**btn) for btn in row]
                            for row in reply_markup_spec
                        ]
                    )
                await bot.send_message(
                    chat_id=user_telegram_id,
                    text=message,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                )
            finally:
                await bot.session.close()

        asyncio.run(_send())
        logger.info(f"Telegram notification sent to {user_telegram_id}")
        return {"success": True, "user_telegram_id": user_telegram_id}

    except TelegramForbiddenError:
        logger.warning(f"User {user_telegram_id} has blocked the bot — skipping")
        return {"success": False, "reason": "blocked"}
    except TelegramBadRequest as exc:
        logger.warning(f"Bad request sending to {user_telegram_id}: {exc}")
        return {"success": False, "reason": "bad_request"}
    except Exception as exc:
        logger.error(
            f"Failed to send Telegram notification to {user_telegram_id}: {exc}"
        )
        self.retry(exc=exc)


@celery_app.task
def send_new_listing_notifications(listing_id: str) -> Dict[str, Any]:
    """Match a new listing against user notification preferences and notify."""
    return asyncio.run(_send_new_listing_notifications(listing_id))


async def _send_new_listing_notifications(listing_id: str) -> Dict[str, Any]:
    """Core async logic for matching and dispatching notifications."""
    async with _get_session() as db:
        # 1. Fetch listing and its seller's user_id
        result = await db.execute(
            select(Listing)
            .where(Listing.id == listing_id)
            .options(selectinload(Listing.seller))
        )
        listing = result.scalar_one_or_none()

        if not listing:
            logger.warning(f"Listing {listing_id} not found — skipping notifications")
            return {"listing_id": listing_id, "notifications_sent": 0}

        if listing.moderation_status != ModerationStatus.APPROVED:
            logger.info(f"Listing {listing_id} not approved — skipping notifications")
            return {"listing_id": listing_id, "notifications_sent": 0}

        if listing.status != ListingStatus.ACTIVE:
            logger.info(f"Listing {listing_id} not active — skipping notifications")
            return {"listing_id": listing_id, "notifications_sent": 0}

        # Determine the listing owner's user_id to exclude
        owner_user_id = None
        if listing.seller:
            owner_user_id = listing.seller.user_id

        listing_attrs = {
            "id": str(listing.id),
            "listing_type": listing.type.value,
            "property_type": listing.property_type.value,
            "district": listing.district,
            "price": listing.price,
            "rooms": listing.rooms,
            "currency": listing.currency.value,
        }

        # Stage 1 — per-SavedSearch matching (more specific, runs first).
        # Creates "Новое по вашему поиску" notifications with the search
        # name. Must run before global prefs so the dedup set ensures the
        # user gets the specific notification, not the generic one.
        saved_result = await _match_saved_searches(
            db, listing, listing_attrs, owner_user_id
        )

        # Stage 2 — global NotificationPreferences matching (generic
        # fallback). Users already notified by saved-search stage are
        # skipped automatically via the existing dedup query on
        # (user_id, listing_id). Pass the full ``listing`` so the
        # match-and-notify path can render the same Block D D2
        # inline keyboard as the saved-search path.
        prefs_result = await _match_and_notify(
            db, listing_attrs, owner_user_id, listing=listing
        )

        return {
            "listing_id": listing_id,
            "notifications_sent": (
                prefs_result.get("notifications_sent", 0)
                + saved_result.get("notifications_sent", 0)
            ),
            "telegram_sent": (
                prefs_result.get("telegram_sent", 0)
                + saved_result.get("telegram_sent", 0)
            ),
            "saved_search_matches": saved_result.get("matched_count", 0),
        }


@celery_app.task
def send_crawler_listing_notifications(listing_data: Dict[str, Any]) -> Dict[str, Any]:
    """Match a crawler listing (Telegram/OLX) against user preferences and notify.

    listing_data must contain: id, listing_type, property_type, district, price, rooms, currency.
    """
    return asyncio.run(_send_crawler_listing_notifications(listing_data))


async def _send_crawler_listing_notifications(
    listing_data: Dict[str, Any],
) -> Dict[str, Any]:
    """Async logic for crawler listing notifications."""
    async with _get_session() as db:
        return await _match_and_notify(db, listing_data, owner_user_id=None)


async def _match_saved_searches(
    db: AsyncSession,
    listing: "Listing",
    listing_attrs: Dict[str, Any],
    owner_user_id=None,
) -> Dict[str, Any]:
    """Match a new listing against all saved searches with notify_enabled.

    Creates in-app Notification rows + queues Telegram sends for matches.
    Deduplicates against notifications already created by the global-prefs
    stage so a user never receives two notifications for the same listing.
    """
    from app.api.v1.saved_searches import _filters_to_listing_filters
    from app.db.models import SavedSearch, Seller
    from app.services.listing_push import build_listing_action_kb_spec
    from app.services.saved_search_matcher import _match_listing_to_filters

    listing_id = listing_attrs["id"]

    # Block D D2 — load the listing's seller once for the whole loop so
    # the inline keyboard's "Написать продавцу" URL can include the
    # right telegram_username / phone. Missing seller is fine; the
    # factory just omits the contact row.
    seller: Optional["Seller"] = None
    if listing.seller_id:
        seller_q = await db.execute(
            select(Seller).where(Seller.id == listing.seller_id)
        )
        seller = seller_q.scalar_one_or_none()

    # Load saved searches with notifications enabled, excluding the owner.
    q = (
        select(SavedSearch, User)
        .join(User, SavedSearch.user_id == User.id)
        .where(
            SavedSearch.notify_enabled.is_(True),
            User.deleted_at.is_(None),
        )
    )
    if owner_user_id:
        q = q.where(User.id != owner_user_id)

    rows = (await db.execute(q)).all()
    if not rows:
        return {"matched_count": 0, "notifications_sent": 0, "telegram_sent": 0}

    # Dedup: find users already notified for this listing (from the
    # global-prefs stage that ran just before us).
    existing = await db.execute(
        select(Notification.user_id).where(
            Notification.listing_id == listing_id,
            Notification.type == NotificationType.NEW_LISTING,
        )
    )
    already_notified = {row[0] for row in existing.all()}

    r = _get_sync_redis()
    today_str = date.today().isoformat()
    matched = 0
    in_app = 0
    tg_count = 0

    for saved, user in rows:
        if user.id in already_notified:
            logger.info(
                "saved-search skip user=%s listing=%s reason=already_notified",
                user.id,
                listing_id,
            )
            continue

        # Hydrate JSONB → ListingFilters and run the matcher.
        filters = _filters_to_listing_filters(saved.filters or {})
        if not _match_listing_to_filters(listing, filters):
            logger.info(
                "saved-search skip user=%s listing=%s reason=filter_mismatch search_id=%s",
                user.id,
                listing_id,
                saved.id,
            )
            continue

        matched += 1

        # Check the user's NotificationPreferences for pause + daily limit.
        prefs_result = await db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user.id
            )
        )
        prefs = prefs_result.scalar_one_or_none()

        # Saved-search notifications respect the paused toggle.
        # Preferences notifications (in _match_and_notify) are NOT gated
        # by paused — they always fire.
        if prefs and prefs.paused:
            logger.info(
                "saved-search skip user=%s listing=%s reason=paused",
                user.id,
                listing_id,
            )
            continue

        daily_limit = prefs.daily_limit if prefs else 10
        if not _check_and_increment_daily_limit(r, user.id, daily_limit, today_str):
            logger.info(
                "saved-search skip user=%s listing=%s reason=daily_limit limit=%d",
                user.id,
                listing_id,
                daily_limit,
            )
            continue

        lang = user.language if user.language in ("ru", "uz") else "ru"
        search_name = saved.name or saved.query or ""

        listing_type = listing_attrs.get("listing_type", "")
        property_type = listing_attrs.get("property_type", "")
        district = listing_attrs.get("district") or "—"
        price_val = listing_attrs.get("price")
        currency = listing_attrs.get("currency", "USD")
        rooms = listing_attrs.get("rooms")
        currency_symbol = "$" if currency == "USD" else "сум"

        property_label = _PROPERTY_TYPE_LABELS[lang].get(property_type, property_type)
        listing_type_label = _LISTING_TYPE_LABELS[lang].get(listing_type, listing_type)
        rooms_text = _ROOMS_TEXT[lang].format(n=rooms) if rooms else ""
        price_str = f"{price_val:,} {currency_symbol}" if price_val else "—"

        fmt = dict(
            search_name=search_name or "Без названия",
            listing_type=listing_type_label,
            property_type=property_label,
            rooms_text=rooms_text,
            district=district,
            price=price_str,
            link=_listing_deep_link(listing_id),
        )

        # In-app notification — always created. source="saved_search"
        # lets the frontend pick the right label/icon without title
        # parsing.
        notification = Notification(
            user_id=user.id,
            type=NotificationType.NEW_LISTING,
            source="saved_search",
            title=_SAVED_SEARCH_TITLE[lang],
            message=_SAVED_SEARCH_MESSAGE[lang].format(**fmt),
            listing_id=listing_id,
        )
        db.add(notification)
        in_app += 1
        already_notified.add(user.id)  # prevent further dups in this run

        # Telegram — saved-search respects paused + time window.
        if not user.telegram_id:
            logger.info(
                "saved-search tg-skip user=%s listing=%s reason=no_telegram_id",
                user.id,
                listing_id,
            )
        elif prefs and prefs.paused:
            logger.info(
                "saved-search tg-skip user=%s listing=%s reason=paused",
                user.id,
                listing_id,
            )
        elif prefs and not _is_within_time_window(prefs):
            logger.info(
                "saved-search tg-skip user=%s listing=%s reason=time_window window=%s-%s",
                user.id,
                listing_id,
                prefs.time_start,
                prefs.time_end,
            )
        else:
            # Block D D2 — render the inline keyboard against the
            # user's full language (incl. uz_cyrl). The push body uses
            # the constrained ``lang`` because the message templates
            # are still ru/uz-only (i18n sweep is a follow-up).
            try:
                kb_spec = build_listing_action_kb_spec(
                    listing, seller, user.language or lang
                )
            except Exception:
                logger.warning(
                    "saved-search kb build failed user=%s listing=%s",
                    user.id,
                    listing_id,
                    exc_info=True,
                )
                kb_spec = None
            send_telegram_notification.delay(
                user.telegram_id,
                _SAVED_SEARCH_TELEGRAM[lang].format(**fmt),
                "HTML",
                kb_spec,
            )
            tg_count += 1
            logger.info(
                "saved-search tg-sent user=%s listing=%s",
                user.id,
                listing_id,
            )

    await db.commit()
    r.close()

    logger.info(
        "Listing %s: saved-search stage matched=%d in_app=%d tg=%d",
        listing_id,
        matched,
        in_app,
        tg_count,
    )
    return {
        "matched_count": matched,
        "notifications_sent": in_app,
        "telegram_sent": tg_count,
    }


async def _match_and_notify(
    db: AsyncSession,
    listing_attrs: Dict[str, Any],
    owner_user_id=None,
    *,
    listing: Optional["Listing"] = None,
) -> Dict[str, Any]:
    """Shared matching and dispatch logic for all listing sources.

    listing_attrs must contain: id, listing_type, property_type, district, price, rooms, currency.

    ``listing`` (optional, Block D D2): when supplied, the function
    renders the standard buyer-facing inline keyboard alongside each
    Telegram push. Callers that only have a dict (e.g. the crawler
    pre-conversion path) leave it None — pushes go out as plain HTML.
    """
    from app.db.models import Seller
    from app.services.listing_push import build_listing_action_kb_spec

    listing_id = listing_attrs["id"]

    # Pre-load the seller once if we have a listing handle.
    seller: Optional["Seller"] = None
    if listing is not None and listing.seller_id:
        seller_q = await db.execute(
            select(Seller).where(Seller.id == listing.seller_id)
        )
        seller = seller_q.scalar_one_or_none()
    listing_type = listing_attrs["listing_type"]
    property_type = listing_attrs["property_type"]
    district = listing_attrs.get("district")
    price = listing_attrs.get("price")
    rooms = listing_attrs.get("rooms")
    currency = listing_attrs.get("currency", "USD")

    # Query users with matching notification preferences
    NP = NotificationPreferences
    query = (
        select(NP, User)
        .join(User, NP.user_id == User.id)
        .where(User.deleted_at.is_(None))
    )

    # Exclude listing owner
    if owner_user_id:
        query = query.where(User.id != owner_user_id)

    # Filter: listing_types (empty = match all)
    query = query.where(
        or_(
            NP.listing_types.is_(None),
            func.array_length(NP.listing_types, 1).is_(None),
            literal(listing_type) == func.any_(NP.listing_types),
        )
    )

    # Filter: property_types (empty = match all)
    query = query.where(
        or_(
            NP.property_types.is_(None),
            func.array_length(NP.property_types, 1).is_(None),
            literal(property_type) == func.any_(NP.property_types),
        )
    )

    # Filter: districts (empty = match all)
    if district:
        query = query.where(
            or_(
                NP.districts.is_(None),
                func.array_length(NP.districts, 1).is_(None),
                literal(district) == func.any_(NP.districts),
            )
        )

    # Filter: price range
    if price is not None:
        query = query.where(or_(NP.price_min.is_(None), literal(price) >= NP.price_min))
        query = query.where(or_(NP.price_max.is_(None), literal(price) <= NP.price_max))

    # Filter: rooms (empty = match all)
    if rooms is not None:
        query = query.where(
            or_(
                NP.rooms.is_(None),
                func.array_length(NP.rooms, 1).is_(None),
                literal(rooms) == func.any_(NP.rooms),
            )
        )

    result = await db.execute(query)
    rows = result.all()

    # Match-transparency: explain why any non-owner user with prefs was
    # filtered out by the SQL query above. Evaluates each filter
    # locally and logs the first reason that excludes them.
    await _log_prefs_rejections(
        db,
        listing_id,
        listing_type,
        property_type,
        district,
        price,
        rooms,
        owner_user_id,
        matched_user_ids={u.id for _, u in rows},
    )

    if not rows:
        logger.info(f"No matching users for listing {listing_id}")
        return {"listing_id": listing_id, "notifications_sent": 0}

    # Create notifications and dispatch Telegram messages.
    # No cross-stage dedup: preferences notifications fire independently
    # of saved-search notifications. A user can receive BOTH for the same
    # listing — one generic "Новое объявление" from prefs and one specific
    # "Новое по вашему поиску" from saved-search. The user wants both.
    r = _get_sync_redis()
    today_str = date.today().isoformat()
    in_app_count = 0
    telegram_count = 0

    currency_symbol = "$" if currency == "USD" else "сум"

    for prefs, user in rows:
        # Skip if user has disabled this notification type
        if "new_listing" in (prefs.disabled_types or []):
            logger.info(
                "prefs skip user=%s listing=%s reason=type_disabled",
                user.id,
                listing_id,
            )
            continue

        # Preferences notifications are ALWAYS active regardless of the
        # paused toggle. The paused flag only controls saved-search
        # notifications (handled in _match_saved_searches). This matches
        # the product requirement: "preferences should always work."

        lang = user.language if user.language in ("ru", "uz") else "ru"

        property_label = _PROPERTY_TYPE_LABELS[lang].get(property_type, property_type)
        listing_type_label = _LISTING_TYPE_LABELS[lang].get(listing_type, listing_type)

        rooms_text = ""
        if rooms:
            rooms_text = _ROOMS_TEXT[lang].format(n=rooms)

        fmt = dict(
            listing_type=listing_type_label,
            property_type=property_label,
            rooms_text=rooms_text,
            district=district or "—",
            price=f"{price:,} {currency_symbol}" if price else "—",
        )
        fmt["link"] = _listing_deep_link(listing_id)
        texts = {
            "title": _TITLE_TEMPLATES[lang],
            "message": _MESSAGE_TEMPLATES[lang].format(**fmt),
            "telegram_message": _TELEGRAM_TEMPLATES[lang].format(**fmt),
        }

        # In-app notification — source="preferences" distinguishes it
        # from saved-search rows without title inspection.
        notification = Notification(
            user_id=user.id,
            type=NotificationType.NEW_LISTING,
            source="preferences",
            title=texts["title"],
            message=texts["message"],
            listing_id=listing_id,
        )
        db.add(notification)
        in_app_count += 1

        # Preferences Telegram: fires regardless of paused or time
        # window. Only the daily limit gates it.
        if not user.telegram_id:
            logger.info(
                "prefs tg-skip user=%s listing=%s reason=no_telegram_id",
                user.id,
                listing_id,
            )
        elif not _check_and_increment_daily_limit(
            r, user.id, prefs.daily_limit, today_str
        ):
            logger.info(
                "prefs tg-skip user=%s listing=%s reason=daily_limit limit=%d",
                user.id,
                listing_id,
                prefs.daily_limit,
            )
        else:
            # Block D D2 — attach the buyer-facing keyboard when we
            # have a full Listing handle. Crawler-import path has only
            # the dict and falls back to text-only push.
            kb_spec = None
            if listing is not None:
                try:
                    kb_spec = build_listing_action_kb_spec(
                        listing, seller, user.language or lang
                    )
                except Exception:
                    logger.warning(
                        "prefs kb build failed user=%s listing=%s",
                        user.id,
                        listing_id,
                        exc_info=True,
                    )
            send_telegram_notification.delay(
                user.telegram_id,
                texts["telegram_message"],
                "HTML",
                kb_spec,
            )
            telegram_count += 1
            logger.info(
                "prefs tg-sent user=%s listing=%s",
                user.id,
                listing_id,
            )

    await db.commit()
    r.close()

    logger.info(
        f"Listing {listing_id}: {in_app_count} in-app, {telegram_count} Telegram notifications"
    )
    return {
        "listing_id": listing_id,
        "notifications_sent": in_app_count,
        "telegram_sent": telegram_count,
    }


@celery_app.task
def send_price_drop_notification(
    listing_id: str,
    old_price: int,
    new_price: int,
    currency: str = "USD",
) -> Dict[str, Any]:
    """Send price drop notifications to users who favorited the listing."""
    return asyncio.run(
        _send_price_drop_notification(listing_id, old_price, new_price, currency)
    )


async def _send_price_drop_notification(
    listing_id: str,
    old_price: int,
    new_price: int,
    currency: str,
) -> Dict[str, Any]:
    """Notify users who favorited this listing about a price drop."""
    price_drop_percent = round((old_price - new_price) / old_price * 100, 1)

    logger.info(
        f"Processing price drop notification for listing {listing_id}: "
        f"{old_price} -> {new_price} ({price_drop_percent}% drop)"
    )

    async with _get_session() as db:
        # Find users who favorited this listing
        from app.db.models import Favorite

        fav_query = (
            select(User, NotificationPreferences)
            .join(Favorite, Favorite.user_id == User.id)
            .outerjoin(
                NotificationPreferences, NotificationPreferences.user_id == User.id
            )
            .where(Favorite.listing_id == listing_id, User.deleted_at.is_(None))
        )
        result = await db.execute(fav_query)
        rows = result.all()

        if not rows:
            return {"listing_id": listing_id, "notifications_sent": 0}

        # Idempotency: skip users already notified for this listing's price drop
        existing = await db.execute(
            select(Notification.user_id).where(
                Notification.listing_id == listing_id,
                Notification.type == NotificationType.PRICE_DROP,
            )
        )
        already_notified = {row[0] for row in existing.all()}

        currency_symbol = "$" if currency == "USD" else "сум"
        r = _get_sync_redis()
        today_str = date.today().isoformat()
        in_app_count = 0
        telegram_count = 0

        for user, prefs in rows:
            if user.id in already_notified:
                continue

            # Skip if user has disabled price_drop notifications
            if prefs and "price_drop" in (prefs.disabled_types or []):
                continue

            lang = user.language if user.language in ("ru", "uz") else "ru"
            texts = _build_price_drop_texts(
                lang,
                old_price,
                new_price,
                price_drop_percent,
                currency_symbol,
                listing_id,
            )

            notification = Notification(
                user_id=user.id,
                type=NotificationType.PRICE_DROP,
                title=texts["title"],
                message=texts["message"],
                listing_id=listing_id,
            )
            db.add(notification)
            in_app_count += 1

            if prefs and prefs.enabled and user.telegram_id:
                if _check_and_increment_daily_limit(
                    r, user.id, prefs.daily_limit, today_str
                ):
                    send_telegram_notification.delay(
                        user.telegram_id,
                        texts["telegram_message"],
                        "HTML",
                    )
                    telegram_count += 1

        await db.commit()
        r.close()

    logger.info(
        f"Price drop {listing_id}: {in_app_count} in-app, {telegram_count} Telegram"
    )
    return {
        "listing_id": listing_id,
        "old_price": old_price,
        "new_price": new_price,
        "price_drop_percent": price_drop_percent,
        "notifications_sent": in_app_count,
        "telegram_sent": telegram_count,
    }


@celery_app.task
def cleanup_old_notifications(days: int = 90) -> Dict[str, Any]:
    """Delete notifications older than *days* days."""
    return asyncio.run(_cleanup_old_notifications(days))


async def _cleanup_old_notifications(days: int) -> Dict[str, Any]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    async with _get_session() as db:
        result = await db.execute(
            delete(Notification).where(Notification.created_at < cutoff)
        )
        await db.commit()
        deleted = result.rowcount
    logger.info(f"Cleaned up {deleted} notifications older than {cutoff.isoformat()}")
    return {"cutoff_date": cutoff.isoformat(), "deleted_count": deleted}
