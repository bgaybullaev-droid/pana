"""Block D V2.0 (D2) — prefilled "Написать продавцу" URL builder.

Domain-layer helper for converting a ``Listing`` into a Telegram URL
that opens the seller's chat with a localised opening line pre-typed
in the input box. Caller picks: (a) a Telegram chat URL when the
seller has a ``telegram_username``, (b) a phone-call URL when they
have only a phone, (c) ``None`` when neither is available — caller
should then omit the button entirely.

Telegram URL conventions
========================
- ``https://t.me/<username>?text=<urlencoded>`` — the ``?text=``
  param works only for ``t.me/<username>`` (not for ``tg://user?id=``).
  When the seller has no ``telegram_username`` we degrade to ``tel:``.
- The prefilled text is hard-capped at ~200 chars to stay well below
  Telegram's per-URL practical limits.

Language policy (Block D D2 spec — sender's language, not recipient's)
======================================================================
The intro is rendered on the **buyer's** locale. The seller learns to
read whichever language their leads send in; we don't translate
between users.
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import quote

from app.db.models import Listing, Seller

logger = logging.getLogger(__name__)

# Cap the prefill so the URL stays compact across all Telegram clients.
_MAX_INTRO_CHARS = 200

# Templates per locale. ``{summary}`` is replaced by a short
# structured-params snippet (district / rooms / area / price).
_INTRO_TEMPLATES = {
    "ru": (
        "Здравствуйте! Увидел в PANA ваше объявление: {summary}. "
        "Хочу узнать подробнее."
    ),
    "uz": (
        "Salom! PANA'da e'loningizni ko'rdim: {summary}. "
        "Batafsil bilmoqchiman."
    ),
    "uz_cyrl": (
        "Салом! PANA'да эълонингизни кўрдим: {summary}. "
        "Батафсил билмоқчиман."
    ),
}

# Currency symbols used in the short summary.
_CURRENCY_SYMBOL = {"USD": "$", "UZS": "сум"}


def _short_summary(listing: Listing, lang: str) -> str:
    """Build a one-line listing summary for the prefilled intro.

    Pure formatting — no I/O. Mirrors the format used by the existing
    new-listing push templates so the bot voice stays consistent.
    """
    parts: list[str] = []
    rooms = getattr(listing, "rooms", None)
    if rooms:
        parts.append(f"{rooms}-комн" if lang == "ru" else f"{rooms}-xona")
    district = getattr(listing, "district", None)
    if district:
        parts.append(str(district))
    area = getattr(listing, "area", None)
    if area:
        parts.append(f"{int(area)} м²" if lang == "ru" else f"{int(area)} m²")
    price = getattr(listing, "price", None)
    currency = getattr(listing, "currency", None)
    if price:
        sym = _CURRENCY_SYMBOL.get(
            currency.value if hasattr(currency, "value") else str(currency or ""),
            "",
        )
        parts.append(f"{price:,} {sym}".strip())
    return ", ".join(parts) or "—"


def build_intro_text(listing: Listing, lang: str) -> str:
    """Render the buyer-side opening line. Capped at _MAX_INTRO_CHARS."""
    tmpl = _INTRO_TEMPLATES.get(lang, _INTRO_TEMPLATES["ru"])
    text = tmpl.format(summary=_short_summary(listing, lang))
    if len(text) > _MAX_INTRO_CHARS:
        text = text[: _MAX_INTRO_CHARS - 1].rstrip() + "…"
    return text


def build_seller_chat_url(
    listing: Listing,
    seller: Optional[Seller],
    sender_lang: str,
) -> Optional[str]:
    """Return a chat-open URL for the listing's seller, or ``None``.

    Resolution order:
      1. ``seller.telegram_username`` → ``https://t.me/<u>?text=<intro>``
      2. ``seller.phone`` or ``listing.phone`` → ``tel:<phone>`` (no prefill)
      3. ``None`` — caller should not render any contact button.

    Falls back gracefully across all branches; never raises.
    """
    if seller is not None and seller.telegram_username:
        intro = build_intro_text(listing, sender_lang)
        username = seller.telegram_username.lstrip("@")
        return f"https://t.me/{username}?text={quote(intro)}"

    phone = (seller.phone if seller else None) or getattr(listing, "phone", None)
    if phone:
        # Strip whitespace/punctuation so the tel: URL is canonical.
        cleaned = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
        return f"tel:{cleaned}"

    return None


def is_telegram_url(url: str) -> bool:
    """Cheap predicate for callers that need to label the button differently
    when degrading to phone-only contact."""
    return url.startswith("https://t.me/")
