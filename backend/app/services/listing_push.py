"""Block D V2.0 (D2) — buyer-facing push keyboard factory.

Single source of truth for the inline keyboard attached to every
new-listing push notification. Returns a JSON-serialisable spec so
callers (today: ``workers.tasks.notifications`` via Celery) can hand
it across a task boundary without picklng aiogram objects.

Layout (3 rows, vertical for thumb-friendliness on mobile):

    [ ⭐ В избранное ]      callback_data=fav:add:<listing_id>
    [ ✉️ Написать продавцу ] url=t.me/<seller>?text=<intro>     (or tel:)
    [ Подробнее → ]         url=t.me/<bot>?startapp=listing_<id>

The keyboard is intentionally minimal — no extra interstitial taps,
per the engineering constraint "prioritise UX simplicity over
analytics perfection". The contact button is therefore a plain URL,
not a callback, even though that costs us a signal — explicit
trade-off documented in spec-kit/block-d/decision-pass.

Localisation: all visible text is rendered against ``lang`` so this
factory is reusable for D4 channel posts (which post in the seller's
language) without duplication.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.bot.i18n import t
from app.db.models import Listing, Seller
from app.services import deeplink, seller_contact

logger = logging.getLogger(__name__)


def build_listing_action_kb_spec(
    listing: Listing,
    seller: Optional[Seller],
    lang: str,
    *,
    is_favorited: bool = False,
) -> list[list[dict]]:
    """Return a Telegram inline-keyboard spec for a new-listing push.

    The returned structure matches aiogram's
    ``InlineKeyboardMarkup(inline_keyboard=...)`` shape so the worker
    can reconstruct without intermediate types:

        [
          [{"text": "...", "callback_data": "..."}],
          [{"text": "...", "url": "..."}],
          [{"text": "...", "url": "..."}],
        ]

    Always includes the favorite-toggle and details buttons; omits
    the contact button when the seller has no reachable channel.

    ``is_favorited`` flips the first-row verb. Callers that don't
    know the favorite state (push send time — we assume no) leave
    the default ``False``.
    """
    rows: list[list[dict]] = []

    # Row 1 — favorite toggle. Verb derived from current state.
    if is_favorited:
        rows.append(
            [
                {
                    "text": t(lang, "btn_fav_remove"),
                    "callback_data": f"fav:remove:{listing.id}",
                }
            ]
        )
    else:
        rows.append(
            [
                {
                    "text": t(lang, "btn_fav_add"),
                    "callback_data": f"fav:add:{listing.id}",
                }
            ]
        )

    # Row 2 — contact seller. URL kind, no callback (UX-first).
    contact_url = seller_contact.build_seller_chat_url(listing, seller, lang)
    if contact_url:
        label_key = (
            "btn_contact_seller"
            if seller_contact.is_telegram_url(contact_url)
            else "btn_call_seller"
        )
        rows.append([{"text": t(lang, label_key), "url": contact_url}])

    # Row 3 — open in TWA via the centralised deeplink builder.
    rows.append(
        [
            {
                "text": t(lang, "btn_listing_details"),
                "url": deeplink.build_listing_link(listing.id),
            }
        ]
    )
    return rows
