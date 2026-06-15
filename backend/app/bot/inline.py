"""Block D V2.0 (D5) — Inline Mode handler.

When a user types ``@ucharmarket_bot <query>`` in any Telegram chat,
this handler runs. It parses the query, hits Meilisearch, formats up
to 20 result cards, and returns them with a per-card "Open in
UcharMarket" button that deep-links into the Mini App.

Per Block D guardrails:

- **Thin adapter.** The two domain services (``query_parser``,
  ``bot_search``) own the logic; this file converts their output
  into ``aiogram.types.InlineQueryResult*``.
- **No caching layer.** Telegram's own ``cache_time=60`` parameter
  is free; Redis is not introduced.
- **Conversion-first UX.** Empty / unrecognised queries return
  recent listings or a hint — never an error.
"""

from __future__ import annotations

import html
import logging

from aiogram import Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultPhoto,
    InputTextMessageContent,
)

from app.bot.i18n import DEFAULT_LANGUAGE, language_from_telegram_code, t
from app.services import bot_search, deeplink, query_parser

logger = logging.getLogger(__name__)

inline_router = Router(name="inline_search")

# Telegram caches results client-side; 60s is the spec-defined floor.
# Stale-but-useful trade-off is acceptable for inline search.
_CACHE_TIME_SECONDS = 60


def _html_escape(text: str) -> str:
    """Escape the three characters Telegram's HTML parse_mode is sensitive to.

    The bot runs with a default ``parse_mode="HTML"`` (see ``bot/main.py``),
    so any dynamic text dropped into a sent message must be escaped or a stray
    ``<`` / ``&`` in a listing's district/title breaks the whole message.
    """
    return html.escape(text or "", quote=False)


def _format_card_text(r: bot_search.BotSearchResult, lang: str) -> str:
    """Compact plain-text summary for the inline result's title/description.

    Telegram never renders formatting in the result-list ``title`` /
    ``description`` fields, so this stays plain. The formatted version that
    is posted into the chat lives in :func:`_format_card_html`.
    """
    bits: list[str] = []
    if r.rooms:
        bits.append(f"{r.rooms}-комн" if lang == "ru" else f"{r.rooms}-xona")
    if r.district:
        bits.append(r.district)
    if r.area:
        bits.append(f"{int(r.area)} м²" if lang == "ru" else f"{int(r.area)} m²")
    price = r.price
    if price:
        sym = "$" if r.currency == "USD" else ("сум" if lang == "ru" else "so'm")
        bits.append(f"{price:,} {sym}")
    return ", ".join(bits) if bits else (r.title or r.id)


def _format_card_html(r: bot_search.BotSearchResult, lang: str) -> str:
    """HTML body posted into the chat when an inline result is tapped.

    Renders the room/district headline in bold and the price in bold so the
    card reads at a glance. All dynamic text is HTML-escaped via
    :func:`_html_escape`; the static labels ("2-комн", "м²", currency) carry
    no HTML-special characters.
    """
    head: list[str] = []
    if r.rooms:
        head.append(f"{r.rooms}-комн" if lang == "ru" else f"{r.rooms}-xona")
    if r.district:
        head.append(_html_escape(r.district))
    title_line = " · ".join(head) or _html_escape(r.title or r.id)

    lines = [f"🏠 <b>{title_line}</b>"]

    meta: list[str] = []
    if r.area:
        meta.append(f"{int(r.area)} м²" if lang == "ru" else f"{int(r.area)} m²")
    if r.price:
        sym = "$" if r.currency == "USD" else ("сум" if lang == "ru" else "so'm")
        meta.append(f"💰 <b>{r.price:,} {sym}</b>")
    if meta:
        lines.append(" · ".join(meta))
    return "\n".join(lines)


def _to_inline_result(
    r: bot_search.BotSearchResult, lang: str
) -> InlineQueryResultArticle | InlineQueryResultPhoto:
    """Build one inline result from a BotSearchResult.

    Listings with a usable image render as a photo card
    (``InlineQueryResultPhoto``) — the photo IS the result, with the
    details as caption and the deep-link button; tapping shares the photo.
    Listings without an image fall back to a compact text article so they
    still appear in the list.
    """
    # Plain summary for the result-list labels (never formatted by Telegram);
    # HTML body for the message/caption that is actually posted into the chat.
    plain = _format_card_text(r, lang)
    body_html = _format_card_html(r, lang)
    open_url = deeplink.build_listing_link(r.id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "search_open_in_app"), url=open_url)]
        ]
    )
    if r.photo_url:
        return InlineQueryResultPhoto(
            id=r.id,
            photo_url=r.photo_url,
            thumbnail_url=r.photo_url,
            title=r.title or plain,
            description=plain,
            caption=body_html,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
    return InlineQueryResultArticle(
        id=r.id,
        title=r.title or plain,
        description=plain,
        input_message_content=InputTextMessageContent(
            message_text=body_html,
            parse_mode="HTML",
            disable_web_page_preview=True,
        ),
        reply_markup=keyboard,
    )


def _no_results_article(lang: str) -> InlineQueryResultArticle:
    """Placeholder card for a zero-result inline query.

    Telegram drops the inline popup silently when ``results=[]`` — the
    worst UX, indistinguishable from a broken bot. Returning a single
    explanatory article keeps the popup visible and nudges the user to
    refine the query (or signals an empty index to ops).
    """
    title = t(lang, "inline_no_results")
    hint = t(lang, "inline_no_results_hint")
    return InlineQueryResultArticle(
        id="no_results",
        title=title,
        description=hint,
        input_message_content=InputTextMessageContent(
            message_text=hint,
            disable_web_page_preview=True,
        ),
    )


def _resolve_lang(query: InlineQuery) -> str:
    """Pick the result language for an inline query.

    DECISION_MATRIX D5-Q3: anonymous inline users (we don't have a
    User row keyed by ``from.id`` in scope here) fall back to
    Telegram's ``language_code``. Authenticated lookups happen only
    on the explicit ``/search`` command path, not in inline mode.
    """
    code = getattr(query.from_user, "language_code", None) if query.from_user else None
    return language_from_telegram_code(code) or DEFAULT_LANGUAGE


@inline_router.inline_query()
async def handle_inline_query(query: InlineQuery) -> None:
    """Entry point for ``@ucharmarket_bot <q>`` from any chat."""
    lang = _resolve_lang(query)
    raw = (query.query or "").strip()

    try:
        if not raw:
            # Empty inline query — show the latest listings as examples.
            # Conversion-first: never return zero results without
            # explanation. Telegram silently drops the inline popup
            # when results=[] which is the worst UX.
            results = await bot_search.recent_listings(
                limit=bot_search.DEFAULT_INLINE_LIMIT
            )
        else:
            parsed = query_parser.parse(raw, lang=lang)
            results = await bot_search.search(
                parsed, limit=bot_search.DEFAULT_INLINE_LIMIT
            )

        articles = [_to_inline_result(r, lang) for r in results]
        if not articles:
            # Zero hits: Telegram collapses the inline popup entirely on an
            # empty result list, which reads as a broken bot. Show one
            # "nothing found" card instead. Short cache_time so real
            # results surface as soon as the index has data.
            await query.answer(
                [_no_results_article(lang)],
                cache_time=5,
                is_personal=True,
            )
            return
        await query.answer(
            articles,
            cache_time=_CACHE_TIME_SECONDS,
            # Results are language-dependent (parsed + rendered per the
            # user's locale). is_personal=True keeps Telegram from caching
            # one user's localized output and serving it to everyone in a
            # shared chat — e.g. an Uzbek user getting Russian results.
            is_personal=True,
        )
    except Exception:
        # Fail-soft: log + show the "nothing found" card (not a blank
        # popup) so the user still gets feedback, not a Telegram error.
        logger.exception("inline_query.handler_failed q=%r", raw[:80])
        try:
            # Per-user cache — output is locale-specific (see above).
            await query.answer(
                [_no_results_article(lang)], cache_time=5, is_personal=True
            )
        except Exception:
            pass
