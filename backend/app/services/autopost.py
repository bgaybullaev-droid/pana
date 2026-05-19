"""Block D V2.0 (D4) — channel autoposting domain logic.

Pure domain module: decides what should happen for a given listing
state, renders the post body, and returns dataclasses. The actual
Telegram I/O lives in :mod:`app.services.channel_publisher`.

This separation lets us test "when a listing flips to SOLD, the
caption gets a ПРОДАНО overlay" without standing up an aiogram
fixture — pure functions in, dataclasses out.

Per Block D guardrails:

- **Domain doesn't speak transport.** :func:`render_post_body` returns
  a :class:`RenderedPost`; the bot adapter formats it for Telegram.
- **Testable outside Telegram.** All entry points take plain
  Listing/Seller/User instances.
- **Single source of truth for the post body** — D4 / future
  variations (D4-Q4 footer wording, currency labels) live here, not
  scattered across publish/edit code paths.
- **No I/O.** No DB write, no Telegram call. Caller composes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from app.bot.i18n import t
from app.core.config import settings
from app.db.models import (
    BotChannelPost,
    Listing,
    ListingStatus,
    ListingType,
    Seller,
)
from app.services import deeplink

# Telegram caption hard limit. AI text gets truncated to stay under
# this comfortably alongside the structured params + footer.
_CAPTION_MAX = 1024
_AI_TEXT_MAX = 700

# Telegram media-edit cutoff (D4 spec — 48h).
MEDIA_EDIT_CUTOFF = timedelta(hours=48)


# =============================================================================
# Result types — what the domain hands back to callers
# =============================================================================


@dataclass(frozen=True)
class RenderedPost:
    """Channel-post content in the seller's language.

    The bot adapter turns ``photo_url`` + ``caption`` + ``button_url``
    into an actual ``send_photo`` call with an inline keyboard.
    """

    caption: str  # ≤ _CAPTION_MAX chars
    photo_url: Optional[str]  # primary listing photo, may be None
    button_label: str
    button_url: str


@dataclass(frozen=True)
class TransitionDecision:
    """What the autopost layer should do for a given listing-status flip.

    ``action`` is one of:
      - ``"publish"``: listing went ACTIVE; create a new channel post.
      - ``"mark_sold"``: status flipped to SOLD; rewrite caption with overlay.
      - ``"delete"``: status moved to PAUSED / DELETED / EXPIRED; remove post.
      - ``"noop"``: nothing to do (e.g. transition between two inactive states).
    """

    action: str
    reason: Optional[str] = None


# =============================================================================
# Domain logic
# =============================================================================


def decide_transition(
    *,
    old_status: Optional[ListingStatus],
    new_status: ListingStatus,
    has_existing_post: bool,
) -> TransitionDecision:
    """Return what to do when a listing changes state.

    ``old_status=None`` covers the "listing just appeared in ACTIVE"
    creation path. ``has_existing_post`` tells us whether there's
    already a ``bot_channel_posts`` row to mutate.
    """
    # Same status → nothing changed.
    if old_status == new_status:
        return TransitionDecision("noop", reason="same_status")

    if new_status == ListingStatus.ACTIVE:
        if has_existing_post:
            return TransitionDecision("noop", reason="already_posted")
        return TransitionDecision("publish")

    if new_status == ListingStatus.SOLD and has_existing_post:
        return TransitionDecision("mark_sold")

    # PAUSED, DELETED, EXPIRED — remove the post.
    if new_status in (
        ListingStatus.PAUSED,
        ListingStatus.DELETED,
        ListingStatus.EXPIRED,
    ) and has_existing_post:
        return TransitionDecision("delete")

    return TransitionDecision("noop", reason="no_action_for_status")


def is_post_stale(post: BotChannelPost, listing: Listing) -> bool:
    """Cabinet uses this to decide whether to show the "stale" badge."""
    return post.last_listing_version < listing.version


def media_edit_allowed(post: BotChannelPost, now: Optional[datetime] = None) -> bool:
    """True if Telegram still allows media (photo) edits on this post."""
    now = now or datetime.utcnow()
    return (now - post.posted_at) < MEDIA_EDIT_CUTOFF


# =============================================================================
# Rendering
# =============================================================================


def _short_summary(listing: Listing, lang: str) -> list[str]:
    """Structured one-line params (rooms / area / floor / district)."""
    bits: list[str] = []
    if listing.rooms:
        bits.append(
            f"{listing.rooms}-комн" if lang == "ru" else f"{listing.rooms}-xona"
        )
    if listing.area:
        bits.append(
            f"{int(listing.area)} м²" if lang == "ru" else f"{int(listing.area)} m²"
        )
    if listing.floor and listing.total_floors:
        bits.append(f"{listing.floor}/{listing.total_floors}")
    if listing.district:
        bits.append(listing.district)
    return bits


def _price_line(listing: Listing) -> str:
    if not listing.price:
        return "—"
    cur = (
        listing.currency.value
        if hasattr(listing.currency, "value")
        else str(listing.currency or "")
    )
    sym = "$" if cur == "USD" else "сум"
    return f"{listing.price:,} {sym}"


def _ai_text(listing: Listing, lang: str) -> str:
    """Return the AI description in the requested language, truncated."""
    candidates = {
        "ru": listing.ai_description_ru,
        "uz": listing.ai_description_uz,
        "uz_cyrl": listing.ai_description_uz_cyrl,
    }
    text = (candidates.get(lang) or candidates.get("ru") or "").strip()
    if len(text) > _AI_TEXT_MAX:
        text = text[: _AI_TEXT_MAX - 1].rstrip() + "…"
    return text


def _primary_photo_url(listing: Listing) -> Optional[str]:
    """Pick the listing's main photo URL.

    The ListingImage relationship is ordered by position; we prefer
    ``is_primary=True`` first, then fall back to the lowest-position
    image. Returns None if no images exist.
    """
    images = getattr(listing, "images", None) or []
    for img in images:
        if getattr(img, "is_primary", False):
            return img.original_url
    if images:
        return images[0].original_url
    return None


def render_post_body(
    listing: Listing,
    seller_lang: str,
    *,
    sold_overlay: bool = False,
) -> RenderedPost:
    """Render a channel post for ``listing`` in ``seller_lang``.

    ``sold_overlay=True`` prepends a ПРОДАНО / СДАНО / SOTILDI label
    (chosen from listing.type — sell vs rent). The body is otherwise
    identical so seller's audience sees the same listing details for
    social-proof.
    """
    bits = _short_summary(listing, seller_lang)
    price = _price_line(listing)
    ai = _ai_text(listing, seller_lang)
    footer = t(seller_lang, "autopost_footer")  # "Через @<bot>" etc.

    parts: list[str] = []
    if sold_overlay:
        is_rent = listing.type == ListingType.RENT
        key = "autopost_overlay_rented" if is_rent else "autopost_overlay_sold"
        parts.append(t(seller_lang, key))
        parts.append("")  # blank line

    if bits:
        parts.append(", ".join(bits))
    parts.append(f"💰 {price}")
    if ai:
        parts.append("")
        parts.append(ai)
    parts.append("")
    parts.append(footer)

    caption = "\n".join(parts)
    if len(caption) > _CAPTION_MAX:
        caption = caption[: _CAPTION_MAX - 1].rstrip() + "…"

    return RenderedPost(
        caption=caption,
        photo_url=_primary_photo_url(listing),
        button_label=t(seller_lang, "btn_listing_details"),
        button_url=deeplink.build_listing_link(listing.id),
    )


# =============================================================================
# Connection-readiness check (used by the cabinet UI + service layer)
# =============================================================================


def is_autopost_ready(seller: Seller) -> bool:
    """True if the seller has a verified, enabled channel binding.

    Cabinet uses this to gate the "Подключите канал" prompt vs the
    "Channel connected" view. The Celery layer uses it to decide
    whether to enqueue a publish in the first place.

    Test-period note: the *subscription* gate is a separate concern
    handled by :mod:`app.services.subscriptions`. This function only
    checks the channel-binding state.
    """
    del settings  # unused — kept to flag that the function is
    # subscription-agnostic on purpose.
    return bool(
        seller.autopost_enabled
        and seller.autopost_channel_id
        and seller.autopost_verified_at is not None
    )
