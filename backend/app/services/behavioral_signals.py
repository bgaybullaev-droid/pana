"""Block D V2.0 (D2) — single writer for the personalization signal feed.

Every favorite-toggle (bot push or in-app TWA) funnels through
``record_event``. The recommender (Ф-77 / Ф-78) reads
``behavioral_signals`` directly; this module is the only place
allowed to write to it so dedup + fail-soft semantics stay
centralised.

Event inventory (one row per slot — add a row before adding an event)
=====================================================================

+--------------+-------------+----------+----------------+-----------------+
| event_type   | consumer    | retention| expected value | volume estimate |
+--------------+-------------+----------+----------------+-----------------+
| fav_add      | Ф-77 / Ф-78 |   180d   | HIGH — strong  | ~2K rows/day    |
|              | recommender |          | implicit       |                 |
|              |             |          | interest       |                 |
+--------------+-------------+----------+----------------+-----------------+
| fav_remove   | Ф-77 / Ф-78 |   180d   | MEDIUM — pairs | ~0.5K rows/day  |
|              | recommender |          | with fav_add   |                 |
+--------------+-------------+----------+----------------+-----------------+

No other event types are currently emitted. ``contact_tap``,
``details_tap``, ``view`` constants are reserved for future use but
**only land when a concrete consumer exists** (per
"avoid collecting behavioral data without a concrete consumer").

Design constraints
==================

- **Recommendation signals must never block the primary user flow.**
  Writes run inside a SAVEPOINT so failures (e.g. FK violations,
  transient DB errors) do not poison the caller's outer transaction.
- **Fail-soft on Redis outage.** Dedup is best-effort: when Redis is
  unavailable the write proceeds without dedup, accepting the rare
  duplicate row.
- **No external coordination.** Pure single-DB write; no queues, no
  workers, no event bus.

Deletion path
=============
This subsystem can be removed in a single commit:
1. Drop ``behavioral_signals`` table (downgrade ``prm_behavioral_signals``).
2. Remove the two ``record_event`` calls from ``api/v1/favorites.py``.
3. Remove the two callback handlers from ``bot/handlers.py``.
4. Delete this file.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BehavioralSignal
from app.db.redis import get_redis

logger = logging.getLogger(__name__)

# Emitted events. Add a new constant ONLY after a consumer is committed
# and the table in the docstring above is updated.
EVENT_FAV_ADD = "fav_add"
EVENT_FAV_REMOVE = "fav_remove"

# Reserved but not yet emitted — keep here so callers can reference the
# constants when the consumer arrives; flip to emit by adding the call
# site, not by changing this module.
EVENT_CONTACT_TAP = "contact_tap"        # reserved — no consumer yet
EVENT_VIEW = "view"                      # reserved — no consumer yet
EVENT_DETAILS_TAP = "details_tap"        # reserved — no consumer yet

# Sources. Adding a source requires no schema change; just a new call
# site that passes the value.
SOURCE_PUSH_INLINE = "push_inline"
SOURCE_IN_APP = "in_app"
SOURCE_BOT_SEARCH = "bot_search"          # reserved — D5
SOURCE_INLINE_MODE = "inline_mode"        # reserved — D5

# Tap-storm dedup window. Within this window, identical
# (user, listing, event_type) tuples collapse to one row. Redis-only;
# DB has no uniqueness constraint to keep writes lock-free.
_DEDUP_TTL_SECONDS = 60


async def record_event(
    db: AsyncSession,
    *,
    event_type: str,
    source: str,
    user_id: Optional[UUID] = None,
    listing_id: Optional[UUID] = None,
) -> None:
    """Append one row to ``behavioral_signals``. Fire-and-forget.

    Caller is responsible for committing the transaction. Errors are
    logged at WARNING — never raised — so callbacks and request
    handlers never crash because the signal layer is unhappy.

    Dedup: identical ``(user_id, listing_id, event_type)`` within the
    last 60s is skipped via a Redis NX SET. When Redis is unavailable
    the dedup is bypassed and the row is written anyway; downstream
    consumers tolerate the duplicate.
    """
    if not await _try_acquire_dedup(user_id, listing_id, event_type):
        logger.debug(
            "signals.dedup_skip user=%s listing=%s event=%s",
            user_id,
            listing_id,
            event_type,
        )
        return

    # Wrap the INSERT in a SAVEPOINT so a failure (e.g. a transient
    # FK violation from a race with user deletion) does NOT poison
    # the caller's outer transaction. Without this, a signal failure
    # would propagate to the parent ``commit()`` and break whatever
    # user-facing operation the caller is running — the opposite of
    # "recommendation signals must never block the primary flow."
    try:
        async with db.begin_nested():
            db.add(
                BehavioralSignal(
                    user_id=user_id,
                    listing_id=listing_id,
                    event_type=event_type,
                    source=source,
                )
            )
            # No explicit flush — the savepoint commit at __aexit__
            # flushes implicitly. Any IntegrityError surfaces here
            # and rolls back only the savepoint.
        logger.info(
            "signals.recorded user=%s listing=%s event=%s source=%s",
            user_id,
            listing_id,
            event_type,
            source,
        )
    except Exception:  # pragma: no cover — defensive
        logger.warning(
            "signals.write_failed user=%s listing=%s event=%s source=%s",
            user_id,
            listing_id,
            event_type,
            source,
            exc_info=True,
        )


async def _try_acquire_dedup(
    user_id: Optional[UUID],
    listing_id: Optional[UUID],
    event_type: str,
) -> bool:
    """Return True if the write should proceed, False if dedup'd.

    On any Redis error returns True (fail-open) so the row still
    lands. The cost of a duplicate row << the cost of dropping a
    legitimate signal during a Redis blip.
    """
    if user_id is None or listing_id is None:
        # Anonymous or listing-agnostic signals — never dedup'd.
        return True
    key = f"signals:dedup:{user_id}:{listing_id}:{event_type}"
    try:
        client = await get_redis()
        was_set = await client.set(key, "1", ex=_DEDUP_TTL_SECONDS, nx=True)
        return bool(was_set)
    except Exception:
        logger.debug("signals.dedup_redis_unavailable; proceeding without dedup")
        return True
