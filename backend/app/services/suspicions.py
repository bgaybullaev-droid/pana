"""Phase-2 duplicate-account detection signals.

Two v1 signal functions feed the ``account_suspicion`` queue:

* ``detect_phone_collisions`` — finds users whose primary phone shares
  the same last-9-digit suffix (Uzbekistan numbers are 9 digits after
  the country code, so this catches both ``+998 90 …`` and ``90 …``
  variants of the same number).
* ``detect_similar_names`` — pairs sellers whose company / first /
  last name fragments produce a ``difflib.SequenceMatcher.ratio``
  above ``threshold``. Stdlib-only so no new deps; capped at 100 pairs
  per run to bound CPU cost on large seller pools.

Both signals are idempotent: before INSERT they check whether an open
``AccountSuspicion`` with the same ``primary_user_id`` + ``signal_kind``
already exists, so the daily Celery beat job can rerun safely.
"""

from __future__ import annotations

import logging
from difflib import SequenceMatcher
from typing import Any, Iterable

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AccountSuspicion, Seller, User

logger = logging.getLogger(__name__)

SIGNAL_PHONE_COLLISION = "phone_collision"
SIGNAL_SIMILAR_NAMES = "similar_names"

_SIMILAR_NAMES_PAIR_CAP = 100


def _phone_suffix(raw: str | None, *, length: int = 9) -> str | None:
    """Return the last ``length`` digits of a phone string, or None."""
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) < length:
        return None
    return digits[-length:]


async def _open_suspicion_exists(
    db: AsyncSession,
    *,
    primary_user_id: Any,
    signal_kind: str,
) -> bool:
    """Idempotency guard: is there already an open row for this pair+kind?"""
    stmt = select(AccountSuspicion.id).where(
        AccountSuspicion.primary_user_id == primary_user_id,
        AccountSuspicion.signal_kind == signal_kind,
        AccountSuspicion.status == "open",
    )
    return (await db.execute(stmt)).first() is not None


async def detect_phone_collisions(db: AsyncSession) -> list[dict]:
    """Emit one open suspicion per phone-suffix collision pair.

    Implementation: pull every (user_id, phone) tuple, bucket by the
    last-9-digit suffix, and emit one suspicion per pair that shares
    a bucket. The first user in the pair (by UUID order) is the
    ``primary_user_id``; the others land in ``evidence.user_ids``.
    """
    rows: Iterable[tuple[Any, str | None]] = (
        await db.execute(
            select(User.id, User.phone).where(User.deleted_at.is_(None))
        )
    ).all()

    buckets: dict[str, list[Any]] = {}
    for user_id, phone in rows:
        suffix = _phone_suffix(phone)
        if suffix is None:
            continue
        buckets.setdefault(suffix, []).append(user_id)

    created: list[dict] = []
    for suffix, user_ids in buckets.items():
        if len(user_ids) < 2:
            continue
        sorted_ids = sorted(user_ids, key=str)
        primary = sorted_ids[0]
        if await _open_suspicion_exists(
            db, primary_user_id=primary, signal_kind=SIGNAL_PHONE_COLLISION
        ):
            continue
        evidence = {
            "phone_suffix": suffix,
            "user_ids": [str(uid) for uid in sorted_ids],
        }
        row = AccountSuspicion(
            primary_user_id=primary,
            signal_kind=SIGNAL_PHONE_COLLISION,
            evidence=evidence,
            status="open",
        )
        db.add(row)
        created.append(evidence)

    if created:
        await db.commit()
    logger.info(
        "suspicions.phone_collision: emitted=%d total_buckets=%d",
        len(created),
        len(buckets),
    )
    return created


async def detect_similar_names(
    db: AsyncSession,
    *,
    threshold: float = 0.85,
) -> list[dict]:
    """Emit one suspicion per high-similarity seller name pair.

    Similarity is the stdlib ``difflib.SequenceMatcher.ratio`` over
    the concatenated ``first_name + last_name`` of the seller's owning
    user. Bounded at the top 100 pairs per run so even with O(n^2)
    cost the worker can never blow up on a large seller pool.
    """
    rows: Iterable[tuple[Any, str | None, str | None]] = (
        await db.execute(
            select(Seller.user_id, User.first_name, User.last_name)
            .join(User, User.id == Seller.user_id)
            .where(User.deleted_at.is_(None))
        )
    ).all()

    profiles: list[tuple[Any, str]] = []
    for user_id, first, last in rows:
        full = " ".join(filter(None, [first, last])).strip().lower()
        if len(full) < 3:
            continue
        profiles.append((user_id, full))

    scored: list[tuple[float, Any, Any, str, str]] = []
    for i in range(len(profiles)):
        for j in range(i + 1, len(profiles)):
            uid_a, name_a = profiles[i]
            uid_b, name_b = profiles[j]
            ratio = SequenceMatcher(None, name_a, name_b).ratio()
            if ratio >= threshold:
                scored.append((ratio, uid_a, uid_b, name_a, name_b))

    scored.sort(key=lambda t: t[0], reverse=True)
    scored = scored[:_SIMILAR_NAMES_PAIR_CAP]

    created: list[dict] = []
    for ratio, uid_a, uid_b, name_a, name_b in scored:
        primary = min(uid_a, uid_b, key=str)
        other = uid_b if primary == uid_a else uid_a
        if await _open_suspicion_exists(
            db, primary_user_id=primary, signal_kind=SIGNAL_SIMILAR_NAMES
        ):
            continue
        evidence = {
            "ratio": round(ratio, 4),
            "user_ids": [str(primary), str(other)],
            "names": [name_a, name_b],
        }
        row = AccountSuspicion(
            primary_user_id=primary,
            signal_kind=SIGNAL_SIMILAR_NAMES,
            evidence=evidence,
            status="open",
        )
        db.add(row)
        created.append(evidence)

    if created:
        await db.commit()
    logger.info(
        "suspicions.similar_names: emitted=%d scanned_profiles=%d candidates=%d",
        len(created),
        len(profiles),
        len(scored),
    )
    return created


async def run_all_signals(db: AsyncSession) -> dict[str, int]:
    """Run every detection signal and return per-signal emit counts."""
    phone = await detect_phone_collisions(db)
    names = await detect_similar_names(db)
    return {
        SIGNAL_PHONE_COLLISION: len(phone),
        SIGNAL_SIMILAR_NAMES: len(names),
    }


__all__ = [
    "SIGNAL_PHONE_COLLISION",
    "SIGNAL_SIMILAR_NAMES",
    "detect_phone_collisions",
    "detect_similar_names",
    "run_all_signals",
]
