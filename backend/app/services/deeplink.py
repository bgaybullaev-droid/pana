"""Block D V2.0 (D3) — server-side deep-link builder & resolver.

Single source of truth for every ``t.me/<bot>?start=…`` and
``t.me/<bot>?startapp=…`` URL the backend produces. Bot push messages,
channel posts (D4), share helpers, and B2B onboarding all funnel
through here so emitter format and 64-char limits stay in sync.

Public surface:
    Generation
        build_listing_link(listing_id)         → t.me share URL
        build_filter_link(filters, db, user)   → t.me share URL (writes payload row)
        build_claim_link(user_id, db, ttl)     → t.me /start URL (writes claim_invite)
        build_agent_link(channel, db, ttl)     → t.me /start URL (writes claim_invite)
        build_referral_link(user_id, db)       → t.me /start URL (writes payload row)
    Resolution
        resolve_filter_payload(id, db)         → dict | None (consumes a use)
        consume_claim_invite(id, tg_id, db)    → ClaimInvite | "expired" | "consumed" | None
    Observability
        record_event(prefix, payload, …, db)   → append to deep_link_events

Telegram constraints respected:
    • All opaque IDs are 12 chars from a 32-symbol alphabet
      (Crockford base32 minus I, L, O, U) — URL-safe, copy-paste-safe,
      ~60 bits of entropy.
    • Total payload (prefix + body) ≤ 44 chars even for the longest
      case (``listing_<full-uuid>``); other prefixes ≤ 20 chars.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta
from typing import Any, Mapping, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import ClaimInvite, DeepLinkEvent, DeepLinkPayload

logger = logging.getLogger(__name__)

# Crockford base32 minus I, L, O, U — humans typing it from a marketing
# placard never mistake characters for one another.
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_SHORT_ID_LENGTH = 12

# Outcome enum surfaced in deep_link_events.outcome. Kept in code rather
# than a Postgres ENUM so analytics queries can use simple string compare.
OUTCOME_OPEN = "open"
OUTCOME_RESOLVED = "resolved"
# FU6: a ``filter_<slug>`` marketing link that had no stored short-id but
# decoded into a valid filter via :func:`parse_filter_slug`.
OUTCOME_RESOLVED_SLUG = "resolved_slug"
OUTCOME_REJECTED_UNKNOWN = "rejected_unknown"
OUTCOME_REJECTED_EXPIRED = "rejected_expired"
OUTCOME_REJECTED_CONSUMED = "rejected_consumed"
OUTCOME_REJECTED_MISMATCH = "rejected_mismatch"


# =============================================================================
# Primitives
# =============================================================================


def generate_short_id(length: int = _SHORT_ID_LENGTH) -> str:
    """URL-safe 12-char opaque ID. ~60 bits of entropy at default length."""
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def _bot_username() -> str:
    """Return the bot username for URL construction, defaulting to test bot.

    A misconfigured bot username never crashes the request path; we emit
    a placeholder and log so the issue surfaces in monitoring.
    """
    username = settings.telegram_bot_username or "UcharMarketBot"
    if not settings.telegram_bot_username:
        logger.warning(
            "TELEGRAM_BOT_USERNAME unset; deep links will use placeholder %r",
            username,
        )
    return username


def _start_url(payload: str) -> str:
    """``t.me/<bot>?start=<payload>`` — routes through the bot's CommandStart."""
    return f"https://t.me/{_bot_username()}?start={payload}"


def _startapp_url(payload: str) -> str:
    """``t.me/<bot>?startapp=<payload>`` — opens Mini App directly with start_param."""
    return f"https://t.me/{_bot_username()}?startapp={payload}"


# =============================================================================
# Builders
# =============================================================================


def build_listing_link(listing_id: UUID | str) -> str:
    """Mini-App deep link to a listing-detail page.

    The frontend ``StartParamHandler`` accepts both ``listing_<uuid>``
    (live) and ``obj_<uuid>`` (V2.0 spec). We emit the ``listing_``
    form so already-live notifications and share cards keep matching.
    """
    payload = f"listing_{listing_id}"
    assert len(payload) <= 64, "listing_ payload exceeds 64 chars"
    return _startapp_url(payload)


def build_found_link() -> str:
    """Mini-App deep link that opens the seller's "Found" screen.

    Used by the grouped crawled-match push (A4): one consolidated
    message with an "Open Found" CTA. The frontend ``StartParamHandler``
    special-cases the bare ``found`` token (it has no ``_`` body, so
    ``parseStartParam`` returns ``None`` for it) and routes to
    ``/seller/found``.
    """
    return _startapp_url("found")


def build_notifications_link() -> str:
    """Mini-App deep link that opens the buyer's notifications list.

    Used by the saved-search digest push (FU7): a single consolidated
    "N new" message with an "Open App" CTA. The frontend
    ``StartParamHandler`` special-cases the bare ``notifications`` token
    (no ``_`` body, so ``parseStartParam`` returns ``None``) and routes
    to ``/notifications``.
    """
    return _startapp_url("notifications")


async def build_filter_link(
    filters: Mapping[str, Any],
    db: AsyncSession,
    *,
    created_by_user_id: Optional[UUID] = None,
) -> tuple[str, str]:
    """Persist a filter payload, return ``(short_id, share_url)``.

    Callers receive both the bare ID (for analytics / further mutation)
    and the ready-to-share URL. Collisions on ``id`` are exceptionally
    unlikely (60 bits) but handled with retry.
    """
    for _attempt in range(5):
        short_id = generate_short_id()
        existing = await db.execute(
            select(DeepLinkPayload.id).where(DeepLinkPayload.id == short_id)
        )
        if existing.scalar_one_or_none() is None:
            break
    else:
        # Astronomical odds; signal loudly if we ever land here.
        raise RuntimeError("Failed to allocate unique deep-link short id")

    db.add(
        DeepLinkPayload(
            id=short_id,
            kind="filter",
            payload=dict(filters),
            created_by_user_id=created_by_user_id,
        )
    )
    await db.flush()
    logger.info(
        "deeplink.filter.created id=%s by_user=%s keys=%s",
        short_id,
        created_by_user_id,
        sorted(filters.keys()),
    )
    return short_id, _startapp_url(f"filter_{short_id}")


async def build_claim_link(
    pre_imported_user_id: UUID,
    db: AsyncSession,
    *,
    ttl_days: int = 7,
) -> tuple[str, str]:
    """Persist a single-use claim invite, return ``(id, /start URL)``.

    The URL routes through ``/start`` (not ``startapp``) because the
    bot handler needs to verify identity before the Mini App opens.
    """
    short_id = generate_short_id()
    db.add(
        ClaimInvite(
            id=short_id,
            kind="claim",
            pre_imported_user_id=pre_imported_user_id,
            expires_at=datetime.utcnow() + timedelta(days=ttl_days),
        )
    )
    await db.flush()
    logger.info(
        "deeplink.claim.created id=%s user=%s ttl_days=%d",
        short_id,
        pre_imported_user_id,
        ttl_days,
    )
    return short_id, _start_url(f"claim_{short_id}")


async def build_agent_link(
    channel_username: str,
    db: AsyncSession,
    *,
    ttl_days: int = 7,
) -> tuple[str, str]:
    """Persist an agent invite (channel-based B2B onboarding)."""
    cleaned = channel_username.lstrip("@")[:64]
    short_id = generate_short_id()
    db.add(
        ClaimInvite(
            id=short_id,
            kind="agent",
            channel_username=cleaned,
            expires_at=datetime.utcnow() + timedelta(days=ttl_days),
        )
    )
    await db.flush()
    logger.info(
        "deeplink.agent.created id=%s channel=%s ttl_days=%d",
        short_id,
        cleaned,
        ttl_days,
    )
    return short_id, _start_url(f"agent_{short_id}")


async def build_referral_link(
    referrer_user_id: UUID,
    db: AsyncSession,
    *,
    source: Optional[str] = None,
) -> tuple[str, str]:
    """Persist a referral mapping; return ``(id, /start URL)``.

    We don't put ``User.id`` in the payload directly — that would let
    anyone scrape attribution by URL-trying ids. Instead, an opaque
    12-char ID maps back via ``deep_link_payloads`` whose payload
    contains ``{"referrer_user_id": "<uuid>", "source": "..."}``.
    """
    short_id = generate_short_id()
    db.add(
        DeepLinkPayload(
            id=short_id,
            kind="ref",
            payload={
                "referrer_user_id": str(referrer_user_id),
                "source": source,
            },
            created_by_user_id=referrer_user_id,
        )
    )
    await db.flush()
    logger.info(
        "deeplink.ref.created id=%s by=%s source=%s",
        short_id,
        referrer_user_id,
        source,
    )
    return short_id, _start_url(f"ref_{short_id}")


# =============================================================================
# Resolvers
# =============================================================================


async def resolve_filter_payload(
    short_id: str, db: AsyncSession
) -> Optional[DeepLinkPayload]:
    """Look up a ``filter_<id>`` deep link and increment its use-count.

    Returns ``None`` on unknown / wrong-kind ID. Increment is best-effort:
    if commit later fails the count update rolls back too — analytics
    err on the side of undercounting rather than ghost-counting.
    """
    row = await db.execute(
        select(DeepLinkPayload).where(DeepLinkPayload.id == short_id)
    )
    obj = row.scalar_one_or_none()
    if obj is None or obj.kind != "filter":
        return None
    await db.execute(
        update(DeepLinkPayload)
        .where(DeepLinkPayload.id == short_id)
        .values(used_count=DeepLinkPayload.used_count + 1)
    )
    logger.info("deeplink.filter.resolved id=%s use_count=%d", short_id, obj.used_count + 1)
    return obj


# Deal-type tokens accepted in a human slug; synonyms fold into the two
# canonical values the buyer feed understands (``deal_type = sell|rent``).
_SLUG_DEAL_TOKENS: dict[str, str] = {
    "buy": "sell",
    "sale": "sell",
    "sell": "sell",
    "rent": "rent",
}

# Trailing ``<N>rooms`` / ``<N>room`` token (e.g. ``2rooms``, ``3room``).
_SLUG_ROOMS_RE = re.compile(r"^(\d{1,2})rooms?$")


def parse_filter_slug(slug: str) -> Optional[dict]:
    """Decode a human-readable marketing slug into a filter payload (FU6).

    Grammar: ``<district>[_<N>rooms][_buy|_sale|_sell|_rent]`` — e.g.
    ``chilonzor_2rooms_rent`` or ``mirzo_ulugbek_3rooms``. The optional
    rooms/deal tokens are peeled off the tail (either order); whatever
    remains must resolve to a known district through the shared alias
    tables (so ``chilanzar`` / typos still work).

    Returns a dict in the SAME shape the bot writes to
    ``deep_link_payloads`` (``district`` / ``rooms_min`` / ``rooms_max`` /
    ``deal_type``) so the TWA hydration path is identical for stored
    short-ids and synthesised slugs. Returns ``None`` when no district can
    be resolved — the district head is mandatory, so a bare ``2rooms_rent``
    or pure garbage falls through to "unknown" handling.
    """
    if not slug:
        return None

    # Imported lazily: keeps the deeplink module's import graph light and
    # avoids any import-time coupling to the parser's regex compilation.
    from app.core.regions import ALL_DISTRICTS
    from app.services.query_parser import canonical_district

    tokens = slug.lower().split("_")
    deal_type: Optional[str] = None
    rooms: Optional[int] = None

    # Peel optional rooms/deal tokens off the tail (order-independent),
    # stopping at the first token that is neither — that is the district.
    while tokens:
        tail = tokens[-1]
        if deal_type is None and tail in _SLUG_DEAL_TOKENS:
            deal_type = _SLUG_DEAL_TOKENS[tail]
            tokens.pop()
            continue
        rooms_match = _SLUG_ROOMS_RE.match(tail)
        if rooms is None and rooms_match and 1 <= int(rooms_match.group(1)) <= 9:
            rooms = int(rooms_match.group(1))
            tokens.pop()
            continue
        break

    if not tokens:
        return None  # rooms/deal only, no district → not a valid filter slug

    candidate = "_".join(tokens)
    if candidate in ALL_DISTRICTS:
        district = candidate
    else:
        district = canonical_district(candidate) or canonical_district(
            candidate.replace("_", " ")
        )
    if not district:
        return None

    payload: dict[str, Any] = {"district": district}
    if rooms is not None:
        payload["rooms_min"] = rooms
        payload["rooms_max"] = rooms
    if deal_type is not None:
        payload["deal_type"] = deal_type
    return payload


async def resolve_referral_payload(
    short_id: str, db: AsyncSession
) -> Optional[dict]:
    """Look up a ``ref_<id>`` payload. Returns the raw dict or None."""
    row = await db.execute(
        select(DeepLinkPayload).where(
            DeepLinkPayload.id == short_id, DeepLinkPayload.kind == "ref"
        )
    )
    obj = row.scalar_one_or_none()
    return obj.payload if obj is not None else None


async def consume_claim_invite(
    short_id: str,
    consumer_telegram_id: int,
    db: AsyncSession,
    *,
    expected_kind: Optional[str] = None,
) -> tuple[Optional[ClaimInvite], str]:
    """Atomically claim a single-use invite.

    Returns ``(invite, outcome)`` where ``outcome`` is one of:
        ``"resolved"``           — consumed; bot should route to Found
        ``"rejected_unknown"``   — id never existed (or wrong kind)
        ``"rejected_expired"``   — past expires_at
        ``"rejected_consumed"``  — already used

    Implementation acquires a row-level lock so two simultaneous
    consumers can't both succeed.
    """
    locked = await db.execute(
        select(ClaimInvite)
        .where(ClaimInvite.id == short_id)
        .with_for_update()
    )
    invite = locked.scalar_one_or_none()
    if invite is None:
        return None, OUTCOME_REJECTED_UNKNOWN
    if expected_kind is not None and invite.kind != expected_kind:
        return None, OUTCOME_REJECTED_UNKNOWN
    if invite.used_at is not None:
        return None, OUTCOME_REJECTED_CONSUMED
    if invite.expires_at <= datetime.utcnow():
        return None, OUTCOME_REJECTED_EXPIRED

    invite.used_at = datetime.utcnow()
    invite.used_by_telegram_id = consumer_telegram_id
    await db.flush()
    logger.info(
        "deeplink.claim.consumed id=%s kind=%s tg=%s",
        short_id,
        invite.kind,
        consumer_telegram_id,
    )
    return invite, OUTCOME_RESOLVED


# =============================================================================
# Observability
# =============================================================================


async def record_event(
    prefix: str,
    payload: str,
    db: AsyncSession,
    *,
    user_id: Optional[UUID] = None,
    is_new_user: bool = False,
    outcome: str = OUTCOME_OPEN,
) -> None:
    """Append one row to ``deep_link_events``. Fire-and-forget on errors.

    Caller is responsible for committing the session. Errors here are
    logged but never re-raised — analytics must not break the user
    experience.
    """
    try:
        db.add(
            DeepLinkEvent(
                prefix=prefix,
                payload=payload[:64],
                user_id=user_id,
                is_new_user=is_new_user,
                outcome=outcome,
            )
        )
        await db.flush()
    except Exception:  # pragma: no cover — defensive
        logger.exception(
            "deeplink.event.record_failed prefix=%s payload=%s", prefix, payload
        )


# =============================================================================
# HMAC helpers (referral abuse guard)
# =============================================================================


# =============================================================================
# Pending-referral plumbing (Block D D3 — ref_ attribution)
# =============================================================================
#
# The bot dispatcher sees ``/start ref_<id>`` before the user has a
# User row. We stash the referrer mapping in Redis keyed by telegram_id;
# the /auth/* user-create endpoints read it once and write the
# attribution to ``User.referred_by_user_id``. Pure observation, fully
# fail-soft.

_PENDING_REF_TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _pending_ref_key(telegram_id: int) -> str:
    return f"deeplink:pending_ref:{telegram_id}"


async def stash_pending_referral(
    *,
    telegram_id: int,
    referrer_user_id: str,
    source: Optional[str] = None,
) -> None:
    """Remember that ``telegram_id`` arrived via ``ref_<id>`` from
    ``referrer_user_id``. Caller (bot dispatcher) writes; the /auth/*
    user-create path reads via :func:`consume_pending_referral`.

    Fail-soft on Redis outage: attribution is observational, so a
    Redis miss simply means we lose attribution for this conversion.
    """
    try:
        from app.db.redis import get_redis

        client = await get_redis()
        await client.set(
            _pending_ref_key(telegram_id),
            f"{referrer_user_id}|{source or ''}",
            ex=_PENDING_REF_TTL_SECONDS,
        )
    except Exception:
        logger.warning(
            "deeplink.ref.stash_failed telegram_id=%s — Redis unavailable",
            telegram_id,
        )


async def consume_pending_referral(
    telegram_id: int,
) -> Optional[tuple[str, Optional[str]]]:
    """Return ``(referrer_user_id, source)`` for ``telegram_id`` if any,
    and atomically remove the key so the same referral can never be
    applied twice. Returns ``None`` on cache miss or Redis outage.

    Caller is responsible for self-referral checks and for verifying
    that the new user's ``referred_by_user_id`` is currently NULL
    before persisting.
    """
    try:
        from app.db.redis import get_redis

        client = await get_redis()
        key = _pending_ref_key(telegram_id)
        raw = await client.get(key)
        if raw is None:
            return None
        await client.delete(key)
        # Stored shape: "<uuid>|<source>"
        text = raw.decode("utf-8") if isinstance(raw, (bytes, bytearray)) else str(raw)
        if "|" not in text:
            return text, None
        ref_id, source = text.split("|", 1)
        return ref_id, (source or None)
    except Exception:
        logger.warning(
            "deeplink.ref.consume_failed telegram_id=%s — Redis unavailable",
            telegram_id,
        )
        return None


# =============================================================================
# HMAC helpers (reserved for future stateless ref IDs)
# =============================================================================


def _hmac_short_id(seed: str) -> str:
    """Deterministic short ID derived from ``User.id`` for referrer fingerprint.

    Not used today (we store the referrer in deep_link_payloads.payload
    so we don't need a reversible function). Exported for future use
    if we ever want stateless referral IDs.
    """
    digest = hmac.new(
        settings.jwt_secret_key.encode(),
        seed.encode(),
        hashlib.sha256,
    ).digest()
    # Map 8 bytes → 13 alphabet chars; truncate to standard length.
    raw = int.from_bytes(digest[:8], "big")
    out: list[str] = []
    n = raw
    while n > 0 and len(out) < _SHORT_ID_LENGTH:
        out.append(_ALPHABET[n % len(_ALPHABET)])
        n //= len(_ALPHABET)
    return "".join(out).rjust(_SHORT_ID_LENGTH, _ALPHABET[0])
