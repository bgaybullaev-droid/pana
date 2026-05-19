"""PR-T — phase-2 referral program endpoints.

Cabinet surface for the referral program. Two routes:

    GET  /seller/referrals             — hero card + stats + recent events
    POST /seller/referrals/regenerate  — rotate the code (rate-limited)

Both endpoints require an authenticated user but NOT seller scope —
buyers can refer too, and we don't want to make them register as a
seller just to grab a share link.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.db.models import User
from app.services.referrals import (
    ensure_referral_code,
    get_recent_events,
    get_stats,
    regenerate_referral_code,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/seller/referrals", tags=["Referrals (PR-T)"])

# ─────────────────────────────────────────────────────────────────────
# Rate-limit window for /regenerate
# ─────────────────────────────────────────────────────────────────────
#
# One regenerate per user per 24h. Enforced via Redis SETNX so a
# logged-in user can't flood our DB with code allocations. Fail-open
# on Redis outage — better to allow one extra regenerate than to
# block a legit user during an infra blip.
_REGEN_TTL_SECONDS = 24 * 3600


# ─────────────────────────────────────────────────────────────────────
# Schemas
# ─────────────────────────────────────────────────────────────────────


class ReferralEventOut(BaseModel):
    referred_user_id: str
    event_type: str
    created_at: str


class ReferralStats(BaseModel):
    invited_count: int
    qualified_count: int
    total_rewards_micros: int


class ReferralOverview(BaseModel):
    referral_code: str
    share_url: str
    stats: ReferralStats
    recent_events: list[ReferralEventOut]


class RegenerateResponse(BaseModel):
    referral_code: str
    share_url: str


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _build_share_url(code: str) -> str:
    """Compose the ``t.me`` share URL for a referral code.

    Falls back to a placeholder bot name when the env var is unset so
    local dev doesn't error out — production deploys must configure
    ``TELEGRAM_BOT_USERNAME``.
    """
    bot = settings.telegram_bot_username or "UcharMarketBot"
    return f"https://t.me/{bot}?start=ref_{code}"


async def _check_regen_rate_limit(user_id: str) -> Optional[int]:
    """Return seconds until next allowed regenerate, or ``None`` if OK.

    Uses Redis SETNX with TTL so the limit auto-resets. Fail-open: if
    Redis is down we let the request through (logged), which is
    consistent with the rest of our soft-rate-limit policy.
    """
    try:
        from app.db.redis import get_redis

        client = await get_redis()
        key = f"referral:regen:{user_id}"
        # NX = only set if not exists; EX = expiry seconds.
        ok = await client.set(key, b"1", nx=True, ex=_REGEN_TTL_SECONDS)
        if ok:
            return None
        ttl = await client.ttl(key)
        return int(ttl) if ttl and ttl > 0 else _REGEN_TTL_SECONDS
    except Exception:
        logger.warning(
            "referral.regen.rate_check_failed user=%s — Redis unavailable",
            user_id,
            exc_info=True,
        )
        return None


# ─────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=ReferralOverview)
async def get_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReferralOverview:
    """Cabinet hero data. Auto-creates a code on first call."""
    code = await ensure_referral_code(db, user)
    await db.commit()

    stats = await get_stats(db, user.id)
    events = await get_recent_events(db, user.id, limit=20)

    return ReferralOverview(
        referral_code=code,
        share_url=_build_share_url(code),
        stats=ReferralStats(**stats),
        recent_events=[
            ReferralEventOut(
                referred_user_id=str(e.referred_user_id),
                event_type=e.event_type,
                created_at=e.created_at.isoformat(),
            )
            for e in events
        ],
    )


@router.post("/regenerate", response_model=RegenerateResponse)
async def regenerate(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegenerateResponse:
    """Rotate the user's referral code. Rate-limited to 1 per 24h."""
    retry_in = await _check_regen_rate_limit(str(user.id))
    if retry_in is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "retry_after_seconds": retry_in},
        )

    code = await regenerate_referral_code(db, user)
    await db.commit()
    logger.info("referral.code.regenerated user=%s new_code=%s", user.id, code)
    return RegenerateResponse(
        referral_code=code,
        share_url=_build_share_url(code),
    )
