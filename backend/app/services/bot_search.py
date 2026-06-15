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

from app.services.listing_normalize import (
    crawled_photo_url,
    native_primary_photo,
    native_to_canonical,
    olx_to_canonical,
    telegram_to_canonical,
)
from app.services.query_parser import (
    ParsedQuery,
    canonical_district,
    district_search_terms,
)

logger = logging.getLogger(__name__)

# Default render language for results when a caller doesn't pass one (the
# bot resolves the user's locale and threads it through). Kept as a bare
# string so this service never imports the bot layer.
DEFAULT_RESULT_LANG = "ru"

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


def _from_canonical(canonical, photo_url: Optional[str]) -> BotSearchResult:
    """Project the shared canonical object onto the bot's result card.

    The bot shows only a handful of fields; the heavy lifting (normalized
    type/property_type, currency, the ready human ``title``) is done once in
    ``services/listing_normalize``. ``photo_url`` is resolved separately via
    the shared photo helpers because the bot wants the lighter thumbnail, not
    the canonical detail-page image list.
    """
    price = canonical.price
    return BotSearchResult(
        id=str(canonical.id),
        title=canonical.title,
        district=canonical.district,
        rooms=canonical.rooms,
        area=canonical.area,
        price=int(price) if price is not None else None,
        currency=canonical.currency or None,
        deal_type=canonical.type,
        property_type=canonical.property_type,
        photo_url=photo_url,
    )


def _native_to_result(listing, lang: str) -> BotSearchResult:
    return _from_canonical(
        native_to_canonical(listing, lang=lang), native_primary_photo(listing)
    )


def _crawled_to_result(row, source: str, lang: str) -> BotSearchResult:
    to_canonical = olx_to_canonical if source == "olx" else telegram_to_canonical
    return _from_canonical(
        to_canonical(row, lang=lang), crawled_photo_url(getattr(row, "images", None))
    )


# ─────────────────────────────────────────────────────────────────────
# Execution
# ─────────────────────────────────────────────────────────────────────


async def search(
    parsed: ParsedQuery,
    *,
    limit: int = DEFAULT_BOT_LIMIT,
    offset: int = 0,
    lang: str = DEFAULT_RESULT_LANG,
) -> list[BotSearchResult]:
    """Run a search and return up to ``limit`` result cards.

    Reads Postgres across native + crawled tables, newest first. ``offset``
    skips the first N globally-ordered rows — used by Inline Mode to page
    results in as the user scrolls. ``lang`` localizes the generated human
    title (ru / uz / uz_cyrl). Never raises — any failure logs a warning and
    returns an empty list so the caller can show its fallback.
    """
    capped = max(1, min(int(limit), DEFAULT_INLINE_LIMIT))
    off = max(0, int(offset))
    try:
        return await _search_postgres(parsed, capped, off, lang)
    except Exception as exc:
        logger.warning("bot_search: postgres query failed: %s", exc, exc_info=True)
        return []


async def recent_listings(
    limit: int = DEFAULT_INLINE_LIMIT,
    offset: int = 0,
    lang: str = DEFAULT_RESULT_LANG,
) -> list[BotSearchResult]:
    """Empty-query fallback for Inline Mode: most-recent listings (paged)."""
    return await search(
        ParsedQuery(raw_text=""), limit=limit, offset=offset, lang=lang
    )


async def _search_postgres(
    parsed: ParsedQuery, limit: int, offset: int = 0, lang: str = DEFAULT_RESULT_LANG
) -> list[BotSearchResult]:
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
        Seller,
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

    # Newest first per source. To return the global page [offset, offset+limit)
    # after merging, each source must yield at least its first offset+limit rows
    # (the n-th global row is within the first n rows of some single source).
    fetch = offset + limit
    main_q = (
        main_q.options(
            selectinload(Listing.images),
            selectinload(Listing.seller).selectinload(Seller.user),
        )
        .order_by(Listing.created_at.desc())
        .limit(fetch)
    )
    tg_q = tg_q.order_by(TelegramListing.created_at.desc()).limit(fetch)
    olx_q = olx_q.order_by(OLXListing.created_at.desc()).limit(fetch)

    async with async_session_maker() as session:
        main_rows = (await session.execute(main_q)).scalars().all()
        tg_rows = (await session.execute(tg_q)).scalars().all()
        olx_rows = (await session.execute(olx_q)).scalars().all()

        # Map inside the session so any attribute access (incl. eager-loaded
        # images) is safe before the connection is released.
        merged: list[tuple[Optional[datetime], BotSearchResult]] = []
        for listing in main_rows:
            merged.append((listing.created_at, _native_to_result(listing, lang)))
        for row in tg_rows:
            merged.append((row.created_at, _crawled_to_result(row, "telegram", lang)))
        for row in olx_rows:
            merged.append((row.created_at, _crawled_to_result(row, "olx", lang)))

    # Global newest-first merge; rows without a timestamp sort last. Slice out
    # the requested page [offset, offset+limit).
    merged.sort(key=lambda pair: (pair[0] is not None, pair[0]), reverse=True)
    return [result for _, result in merged[offset : offset + limit]]


__all__ = (
    "BotSearchResult",
    "search",
    "recent_listings",
    "DEFAULT_BOT_LIMIT",
    "DEFAULT_INLINE_LIMIT",
)
