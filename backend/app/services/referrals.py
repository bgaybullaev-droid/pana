"""PR-T — phase-2 referral program services.

Three public entry points, in lifecycle order:

    1. :func:`ensure_referral_code` — called by the cabinet GET so each
       user has a shareable code the first time they look. Lazy +
       collision-tolerant; never raises on race.

    2. :func:`attribute_signup` — called by the auth-flow helper after
       the user row is committed. Records a ``signup`` event row.
       Idempotent via the triple-UNIQUE constraint.

    3. :func:`maybe_qualify` — called by domain code whenever the
       referred user takes an action that should count as "qualified"
       (v1: first wallet top-up ≥ 30 000 UZS micros = 30 000 000 000).
       Records a ``qualified`` event and grants the referrer a 5 000 UZS
       reward via :func:`app.services.wallet.deposit` when available, or
       a wallet-tx-less row when wallet plumbing isn't wired.

Why three steps, not one? Attribution is observational and must never
break the auth flow; rewards involve money and must run inside the
caller's outer transaction. Separating them keeps the failure radius
of each step minimal.
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReferralEvent, ReferralReward, User

logger = logging.getLogger(__name__)

# Same alphabet as ``services/deeplink.py`` — Crockford base32 minus
# I, L, O, U. 8 chars at this alphabet → ~40 bits, comfortably collision-free
# even at 10M users.
_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_CODE_LENGTH = 8

# Qualifying threshold for v1: first wallet top-up >= 30 000 UZS.
# Stored in the same smallest-unit convention the wallet uses (UZS=whole UZS,
# not micros). The spec asks for "30 000 UZS"; the wallet's amount column
# is BIGINT smallest-unit. micros confusion lives only in the reward
# amount column — see ``REWARD_AMOUNT_MICROS`` below.
QUALIFYING_TOPUP_AMOUNT_UZS = 30_000

# Reward to the referrer in UZS micros (1 UZS = 1_000_000 micros).
# 5 000 UZS = 5_000_000_000 micros.
REWARD_AMOUNT_MICROS = 5_000 * 1_000_000

REWARD_REASON = "referral_first_topup"


# =============================================================================
# Code generation
# =============================================================================


def generate_referral_code() -> str:
    """Return an 8-char Crockford-alphabet referral code.

    Not cryptographically meaningful — collisions are handled by the
    caller. We just want enough entropy that two new sellers signing
    up in the same second pick different codes >99.999% of the time.
    """
    return "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_LENGTH))


async def ensure_referral_code(db: AsyncSession, user: User) -> str:
    """Return ``user.referral_code``, generating one if absent.

    Persists via ``db.flush`` so callers can build a share URL from the
    same session. Retries on UNIQUE collision; gives up after 5 attempts
    (astronomically unlikely) by raising RuntimeError — the cabinet
    surfaces a generic error in that case.
    """
    if user.referral_code:
        return user.referral_code

    for attempt in range(5):
        candidate = generate_referral_code()
        user.referral_code = candidate
        try:
            await db.flush()
            logger.info(
                "referral.code.allocated user=%s code=%s attempt=%d",
                user.id,
                candidate,
                attempt,
            )
            return candidate
        except IntegrityError:
            # Collision on the UNIQUE index. Roll back and pick another.
            await db.rollback()
            # Re-attach the user to the session — rollback expunged it.
            user = await db.merge(user)
            user.referral_code = None
    raise RuntimeError("could not allocate unique referral_code")


async def regenerate_referral_code(db: AsyncSession, user: User) -> str:
    """Force a fresh code, invalidating the old one.

    The old code's deep-link payload (if any) remains in
    ``deep_link_payloads`` and will resolve to a stale referrer; the
    auth flow's self-referral / already-attributed guards handle that
    gracefully. We do not delete the old code from history because
    other systems may have logged it already.
    """
    user.referral_code = None
    return await ensure_referral_code(db, user)


# =============================================================================
# Attribution
# =============================================================================


async def attribute_signup(
    db: AsyncSession,
    new_user: User,
    referrer_code: Optional[str],
) -> Optional[ReferralEvent]:
    """Record a ``signup`` event when ``new_user`` arrived via ``referrer_code``.

    Returns the event row, or ``None`` if attribution didn't happen
    (unknown code, self-referral, or already attributed). Idempotent
    via the triple-UNIQUE constraint.

    Note: most attribution today flows through the Block D
    ``consume_pending_referral`` helper in ``services/deeplink.py`` —
    that path writes ``users.referred_by_user_id`` directly. This
    function is the "I know the code, write the event" entry point;
    callers that already have ``new_user.referred_by_user_id`` set
    should pass the *resolved* referrer's code here.
    """
    if not referrer_code:
        return None

    referrer = (
        await db.execute(select(User).where(User.referral_code == referrer_code))
    ).scalar_one_or_none()
    if referrer is None:
        logger.info(
            "referral.signup.unknown_code code=%s user=%s",
            referrer_code,
            new_user.id,
        )
        return None
    if referrer.id == new_user.id:
        logger.info(
            "referral.signup.self_referral user=%s", new_user.id
        )
        return None

    event = ReferralEvent(
        referrer_user_id=referrer.id,
        referred_user_id=new_user.id,
        event_type="signup",
        event_metadata={"source": new_user.referral_source},
    )
    db.add(event)
    try:
        await db.flush()
    except IntegrityError:
        # Already attributed — fine, observational.
        await db.rollback()
        logger.info(
            "referral.signup.dup referrer=%s referred=%s",
            referrer.id,
            new_user.id,
        )
        return None

    # Also keep User.referred_by_user_id in sync for backward
    # compatibility with Block D D3 consumers.
    if new_user.referred_by_user_id is None:
        new_user.referred_by_user_id = referrer.id
        await db.flush()

    logger.info(
        "referral.signup.recorded referrer=%s referred=%s",
        referrer.id,
        new_user.id,
    )
    return event


# =============================================================================
# Qualification + reward
# =============================================================================


async def maybe_qualify(
    db: AsyncSession,
    referred_user: User,
    *,
    qualifying_amount_uzs: int = 0,
) -> Optional[ReferralReward]:
    """Mark ``referred_user`` as qualified and reward the referrer.

    v1 qualification rule: first wallet top-up of ≥ 30 000 UZS. Callers
    pass the top-up amount (in whole UZS — same convention as the wallet
    ``Transaction.amount`` column); we no-op for smaller amounts. Returns
    the reward row on success, or ``None`` if the user wasn't referred,
    didn't qualify, or was already rewarded.

    Idempotent: the UNIQUE on (referrer, referred, ``qualified``) ensures
    a second call by a retry-happy caller produces zero side-effects.
    """
    if referred_user.referred_by_user_id is None:
        return None
    if qualifying_amount_uzs < QUALIFYING_TOPUP_AMOUNT_UZS:
        return None

    referrer_id: UUID = referred_user.referred_by_user_id

    # Insert the qualified event first. If it fails the UNIQUE, the user
    # was already rewarded and we bail out without granting a second
    # payout — the row exists in referral_rewards from the first call.
    event = ReferralEvent(
        referrer_user_id=referrer_id,
        referred_user_id=referred_user.id,
        event_type="qualified",
        event_metadata={"amount_uzs": qualifying_amount_uzs},
    )
    db.add(event)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        logger.info(
            "referral.qualified.dup referrer=%s referred=%s",
            referrer_id,
            referred_user.id,
        )
        return None

    # Grant the reward. We try to route money via the wallet service so
    # the audit-log + balance-update plumbing kicks in; if that import
    # path is missing (early-stage envs) we still record the reward row
    # with a NULL wallet_tx_id so admins can settle later.
    wallet_tx_id: Optional[UUID] = None
    try:
        from app.services.wallet import deposit as wallet_deposit
        from app.db.models import Currency  # local import — avoid cycle

        # Wallet uses smallest currency unit (UZS=whole UZS). Convert.
        amount_uzs = REWARD_AMOUNT_MICROS // 1_000_000
        idem_key = f"referral_reward:{referrer_id}:{referred_user.id}"
        tx = await wallet_deposit(
            db,
            user_id=referrer_id,
            amount=amount_uzs,
            idempotency_key=idem_key,
            currency=Currency.UZS,
            metadata={
                "reason": REWARD_REASON,
                "referred_user_id": str(referred_user.id),
            },
        )
        wallet_tx_id = tx.id
    except Exception:
        # Wallet path unavailable — proceed with a wallet-less reward
        # row so the cabinet still shows the entry. Logged loudly so
        # ops notices the gap.
        logger.warning(
            "referral.reward.wallet_unavailable referrer=%s referred=%s "
            "— granting wallet-less reward row",
            referrer_id,
            referred_user.id,
            exc_info=True,
        )

    reward = ReferralReward(
        referrer_user_id=referrer_id,
        amount_micros=REWARD_AMOUNT_MICROS,
        reason=REWARD_REASON,
        wallet_tx_id=wallet_tx_id,
    )
    db.add(reward)
    # Also drop a ``rewarded`` event for clean analytics joins.
    db.add(
        ReferralEvent(
            referrer_user_id=referrer_id,
            referred_user_id=referred_user.id,
            event_type="rewarded",
            event_metadata={"amount_micros": REWARD_AMOUNT_MICROS},
        )
    )
    try:
        await db.flush()
    except IntegrityError:
        # `rewarded` event collision is harmless — keep the reward row.
        await db.rollback()
        # Re-add the reward row alone; the event was the only colliding member.
        reward = ReferralReward(
            referrer_user_id=referrer_id,
            amount_micros=REWARD_AMOUNT_MICROS,
            reason=REWARD_REASON,
            wallet_tx_id=wallet_tx_id,
        )
        db.add(reward)
        await db.flush()

    logger.info(
        "referral.reward.granted referrer=%s referred=%s wallet_tx=%s",
        referrer_id,
        referred_user.id,
        wallet_tx_id,
    )
    return reward


# =============================================================================
# Read helpers
# =============================================================================


async def get_stats(db: AsyncSession, user_id: UUID) -> dict:
    """Aggregate counters for the cabinet hero card.

    Three SELECTs — small enough that no caching is needed at MVP scale.
    """
    invited_count = (
        await db.execute(
            select(func.count(ReferralEvent.id)).where(
                ReferralEvent.referrer_user_id == user_id,
                ReferralEvent.event_type == "signup",
            )
        )
    ).scalar_one()
    qualified_count = (
        await db.execute(
            select(func.count(ReferralEvent.id)).where(
                ReferralEvent.referrer_user_id == user_id,
                ReferralEvent.event_type == "qualified",
            )
        )
    ).scalar_one()
    total_rewards_micros = (
        await db.execute(
            select(func.coalesce(func.sum(ReferralReward.amount_micros), 0)).where(
                ReferralReward.referrer_user_id == user_id,
            )
        )
    ).scalar_one()
    return {
        "invited_count": int(invited_count or 0),
        "qualified_count": int(qualified_count or 0),
        "total_rewards_micros": int(total_rewards_micros or 0),
    }


async def get_recent_events(
    db: AsyncSession, user_id: UUID, *, limit: int = 20
) -> list[ReferralEvent]:
    """Latest ``limit`` events for ``user_id``, newest first."""
    rows = (
        await db.execute(
            select(ReferralEvent)
            .where(ReferralEvent.referrer_user_id == user_id)
            .order_by(ReferralEvent.created_at.desc())
            .limit(limit)
        )
    ).scalars()
    return list(rows)
