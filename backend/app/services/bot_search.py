"""Block D V2.0 (D5) — Postgres executor for bot-side search.

The bot's Inline Mode and ``/search`` read **directly from Postgres**,
across the same three tables the app's mixed feed uses — native
:class:`Listing` plus crawled :class:`TelegramListing` / :class:`OLXListing`
— so the bot returns the exact same inventory the app shows. Postgres is
the source of truth; this deliberately avoids the separate Meilisearch
index, which is not the source of truth, is wiped on every container
rebuild, and has to be repopulated by fragile side channels.

Text matching mirrors the app feed (``GET /listings/feed``): a
case-insensitive ``ILIKE`` substring match, per query token, across each
listing's text columns. Numeric intent the parser extracted (rooms, price
range) is applied as proper column filters. The free-form district name in
the query is matched via ``ILIKE`` on the text columns — the parser's
canonical district *key* (e.g. ``"chilonzor"``) is deliberately NOT used as
an equality filter, because Postgres stores the raw district spelling
(e.g. ``"Чиланзар"``) and the key would never match.

Per Block D guardrails:

- **Domain returns domain objects.** :class:`BotSearchResult` is a plain
  dataclass; ``bot/inline.py`` adapts it to aiogram types.
- **Graceful degradation.** Any DB failure surfaces as an empty list + a
  logged warning; callers show a friendly fallback message.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.services.query_parser import (
    ParsedQuery,
    canonical_district,
    district_search_terms,
)

logger = logging.getLogger(__name__)

# Cap on results returned to the caller. Bot in-chat search shows
# 5–10 (DECISION_MATRIX D5-Q6); Inline Mode shows up to 20 (D5 spec).
DEFAULT_BOT_LIMIT = 10
DEFAULT_INLINE_LIMIT = 20


@dataclass(frozen=True)
class BotSearchResult:
    """One row in the bot's search result list."""

    id: str
    title: Optional[str] = None
    district: Optional[str] = None
    rooms: Optional[int] = None
    area: Optional[float] = None
    price: Optional[int] = None
    currency: Optional[str] = None
    deal_type: Optional[str] = None  # "sell" | "rent"
    property_type: Optional[str] = None
    photo_url: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────
# Free-text tokenisation
# ─────────────────────────────────────────────────────────────────────
#
# Tokens that carry no useful ILIKE signal: bound words ("до"/"от"),
# magnitude markers ("тыс"/"млн"/"k") and currency markers. The numeric
# value itself (and "N-комн" forms) is matched structurally via the parsed
# rooms / price filters, so those tokens are dropped from the text match —
# otherwise a listing whose body says "двухкомнатная" would be wrongly
# excluded for lacking the literal substring "2-комн".

_STOP_TOKENS = {
    "до",
    "от",
    "do",
    "ot",
    "тыс",
    "tys",
    "млн",
    "mln",
    "k",
    "к",
    "m",
    "у.е.",
    "y.e.",
    "у.е",
    "y.e",
    "usd",
    "дол",
    "доллар",
    "сум",
    "сўм",
    "so'm",
    "som",
    "soʻm",
}
_STRIP_CHARS = " .,:;!?-—\"'«»()[]$"
# Any token that starts with a digit is a number-ish fragment — a price,
# room count, area, or a half-typed magnitude like "300мл" / "40k". None
# carry a useful ILIKE signal (district / keyword tokens never start with a
# digit), and the numeric intent is captured by the structured price / rooms
# filters, so they are dropped from the text match. Dropping the whole
# leading-digit class (not just well-formed numbers) is what stops a typo
# like "300мл" becoming a mandatory '%300мл%' substring that returns nothing.
_LEADING_DIGIT_RE = re.compile(r"^\d")
# Bare room-unit word with no leading digit ("комнаты", "комнат", "xonali",
# "honali"): when the user writes "2 комнаты" the digit is a separate token,
# so the word slips past the leading-digit check above. Rooms is a structured
# filter, so this word must not be AND-required against the listing text
# (listings say "2-комн", rarely the literal "комнаты", so requiring it
# wrongly excludes nearly everything).
_ROOM_WORD_RE = re.compile(r"^(?:комн\w*|xona\w*|hona\w*)$", re.IGNORECASE)


def _free_text_tokens(raw: str) -> list[str]:
    """Significant query tokens to ILIKE against the listing text columns.

    Drops short tokens, stop-words, number-ish tokens and bare room-unit
    words (all expressed as structured filters instead). Keeps district
    names, keywords ("квартира", "офис") and landmark/street words.
    """
    tokens: list[str] = []
    for piece in (raw or "").split():
        tok = piece.strip(_STRIP_CHARS).lower()
        if len(tok) < 2:
            continue
        if tok in _STOP_TOKENS:
            continue
        if _LEADING_DIGIT_RE.match(tok) or _ROOM_WORD_RE.match(tok):
            continue
        tokens.append(tok)
    return tokens


def _crawler_photo_url(images) -> Optional[str]:
    """First usable image URL from a crawled listing's JSONB ``images``.

    Crawled rows store ``images`` as a list of absolute URL strings.
    """
    if isinstance(images, list):
        for img in images:
            if isinstance(img, str) and img:
                return img
    return None


def _native_photo_url(listing) -> Optional[str]:
    """Best display photo for a native Listing, mirroring the feed card:
    the ``is_primary`` image, else the first, preferring a lighter variant.

    Relies on the caller eager-loading ``images`` (``selectinload``) so this
    never triggers a lazy load.
    """
    try:
        images = list(getattr(listing, "images", None) or [])
    except Exception:
        return None
    if not images:
        return None
    chosen = next((im for im in images if getattr(im, "is_primary", False)), images[0])
    return (
        getattr(chosen, "medium_url", None)
        or getattr(chosen, "large_url", None)
        or getattr(chosen, "original_url", None)
    )


def _native_to_result(listing) -> BotSearchResult:
    return BotSearchResult(
        id=str(listing.id),
        title=listing.title,
        district=listing.district,
        rooms=listing.rooms,
        area=listing.area,
        price=listing.price,
        currency=listing.currency.value if listing.currency is not None else None,
        deal_type=listing.type.value if listing.type is not None else None,
        property_type=(
            listing.property_type.value if listing.property_type is not None else None
        ),
        photo_url=_native_photo_url(listing),
    )


def _crawled_to_result(row, source: str) -> BotSearchResult:
    del source  # currently unused; kept for call-site symmetry / future use
    price = getattr(row, "price", None)
    currency = getattr(row, "currency", None) or ""
    return BotSearchResult(
        id=str(row.id),
        title=None,  # crawled rows have no title — the card renders from body
        district=getattr(row, "district", None),
        rooms=getattr(row, "rooms", None),
        area=getattr(row, "area_sqm", None),
        price=int(price) if price is not None else None,
        currency=currency.upper() or None,
        deal_type=getattr(row, "listing_type", None) or None,
        property_type=getattr(row, "property_type", None) or None,
        photo_url=_crawler_photo_url(getattr(row, "images", None)),
    )


# ─────────────────────────────────────────────────────────────────────
# Execution
# ─────────────────────────────────────────────────────────────────────


async def search(
    parsed: ParsedQuery,
    *,
    limit: int = DEFAULT_BOT_LIMIT,
) -> list[BotSearchResult]:
    """Run a search and return up to ``limit`` result cards.

    Reads Postgres across native + crawled tables, newest first. Never
    raises — any failure logs a warning and returns an empty list so the
    caller can show its "nothing found" fallback.
    """
    capped = max(1, min(int(limit), DEFAULT_INLINE_LIMIT))
    try:
        return await _search_postgres(parsed, capped)
    except Exception as exc:
        logger.warning("bot_search: postgres query failed: %s", exc, exc_info=True)
        return []


async def recent_listings(limit: int = DEFAULT_INLINE_LIMIT) -> list[BotSearchResult]:
    """Empty-query fallback for Inline Mode: most-recent listings."""
    return await search(ParsedQuery(raw_text=""), limit=limit)


async def _search_postgres(parsed: ParsedQuery, limit: int) -> list[BotSearchResult]:
    """The actual Postgres read. Mirrors the visibility + text-match rules
    of ``GET /listings/feed`` so the bot and the app surface the same rows.
    """
    from sqlalchemy import or_, select
    from sqlalchemy.orm import selectinload

    from app.db.database import async_session_maker
    from app.db.models import (
        Listing,
        ListingStatus,
        ModerationStatus,
        OLXListing,
        TelegramListing,
    )

    tokens = _free_text_tokens(parsed.raw_text)
    rooms = parsed.rooms_min
    price_min = parsed.price_min
    price_max = parsed.price_max

    # A recognised district is matched via ALL its known spellings (Latin +
    # Cyrillic) rather than the single literal the user typed: the crawler
    # stores the district inconsistently ("Чиланзар" / "Chilanzar" /
    # "Chilonzor"), so a one-spelling ILIKE under-returns. Drop the raw
    # district token(s) from the free-text set so we don't AND one narrow
    # spelling on top of the broader OR-expansion applied below.
    district_terms = district_search_terms(parsed.district)
    if district_terms:
        tokens = [
            tok for tok in tokens if canonical_district(tok) != parsed.district
        ]

    # Base visibility — mirror the app's mixed feed, additionally excluding
    # claimed (``converted_listing_id``) crawled rows so a claimed listing
    # is not double-listed (it appears as its native row), and
    # seller-rejected Telegram rows.
    main_q = select(Listing).where(
        Listing.status == ListingStatus.ACTIVE,
        Listing.moderation_status == ModerationStatus.APPROVED,
        Listing.deleted_at.is_(None),
    )
    tg_q = select(TelegramListing).where(
        TelegramListing.converted_listing_id.is_(None),
        TelegramListing.rejected_at.is_(None),
    )
    olx_q = select(OLXListing).where(OLXListing.converted_listing_id.is_(None))

    # Per-token ILIKE, AND-ed together (each token must match somewhere),
    # OR-ed across the text columns — identical semantics to the feed.
    for tok in tokens:
        like = f"%{tok}%"
        main_q = main_q.where(
            or_(
                Listing.title.ilike(like),
                Listing.description.ilike(like),
                Listing.district.ilike(like),
                Listing.address.ilike(like),
            )
        )
        tg_q = tg_q.where(
            or_(
                TelegramListing.description.ilike(like),
                TelegramListing.district.ilike(like),
                TelegramListing.address.ilike(like),
                TelegramListing.raw_text.ilike(like),
            )
        )
        olx_q = olx_q.where(
            or_(
                OLXListing.description.ilike(like),
                OLXListing.district.ilike(like),
                OLXListing.address.ilike(like),
                OLXListing.raw_text.ilike(like),
            )
        )

    # District expansion: the row matches if ANY known spelling of the
    # recognised district appears in any text column. OR-ed across spellings
    # so a Cyrillic query finds Latin-spelled rows and vice versa.
    if district_terms:
        main_q = main_q.where(
            or_(
                *[
                    or_(
                        Listing.title.ilike(f"%{d}%"),
                        Listing.description.ilike(f"%{d}%"),
                        Listing.district.ilike(f"%{d}%"),
                        Listing.address.ilike(f"%{d}%"),
                    )
                    for d in district_terms
                ]
            )
        )
        tg_q = tg_q.where(
            or_(
                *[
                    or_(
                        TelegramListing.description.ilike(f"%{d}%"),
                        TelegramListing.district.ilike(f"%{d}%"),
                        TelegramListing.address.ilike(f"%{d}%"),
                        TelegramListing.raw_text.ilike(f"%{d}%"),
                    )
                    for d in district_terms
                ]
            )
        )
        olx_q = olx_q.where(
            or_(
                *[
                    or_(
                        OLXListing.description.ilike(f"%{d}%"),
                        OLXListing.district.ilike(f"%{d}%"),
                        OLXListing.address.ilike(f"%{d}%"),
                        OLXListing.raw_text.ilike(f"%{d}%"),
                    )
                    for d in district_terms
                ]
            )
        )

    # Structured numeric filters (parser gives min == max for rooms).
    if rooms is not None:
        main_q = main_q.where(Listing.rooms == rooms)
        tg_q = tg_q.where(TelegramListing.rooms == rooms)
        olx_q = olx_q.where(OLXListing.rooms == rooms)
    if price_min is not None:
        main_q = main_q.where(Listing.price >= price_min)
        tg_q = tg_q.where(TelegramListing.price >= price_min)
        olx_q = olx_q.where(OLXListing.price >= price_min)
    if price_max is not None:
        main_q = main_q.where(Listing.price <= price_max)
        tg_q = tg_q.where(TelegramListing.price <= price_max)
        olx_q = olx_q.where(OLXListing.price <= price_max)

    # Newest first per source; fetch up to `limit` from each, then merge.
    main_q = (
        main_q.options(selectinload(Listing.images))
        .order_by(Listing.created_at.desc())
        .limit(limit)
    )
    tg_q = tg_q.order_by(TelegramListing.created_at.desc()).limit(limit)
    olx_q = olx_q.order_by(OLXListing.created_at.desc()).limit(limit)

    async with async_session_maker() as session:
        main_rows = (await session.execute(main_q)).scalars().all()
        tg_rows = (await session.execute(tg_q)).scalars().all()
        olx_rows = (await session.execute(olx_q)).scalars().all()

        # Map inside the session so any attribute access (incl. eager-loaded
        # images) is safe before the connection is released.
        merged: list[tuple[Optional[datetime], BotSearchResult]] = []
        for listing in main_rows:
            merged.append((listing.created_at, _native_to_result(listing)))
        for row in tg_rows:
            merged.append((row.created_at, _crawled_to_result(row, "telegram")))
        for row in olx_rows:
            merged.append((row.created_at, _crawled_to_result(row, "olx")))

    # Global newest-first merge; rows without a timestamp sort last.
    merged.sort(key=lambda pair: (pair[0] is not None, pair[0]), reverse=True)
    return [result for _, result in merged[:limit]]


__all__ = (
    "BotSearchResult",
    "search",
    "recent_listings",
    "DEFAULT_BOT_LIMIT",
    "DEFAULT_INLINE_LIMIT",
)
