"""Block D V2.0 — Subscription gate helper.

Single chokepoint that says "is this seller allowed to use a paid
Cabinet feature right now?" Today: D4 (autoposting). Tomorrow:
whatever else gates on the Cabinet subscription tier.

Behaviour controlled by ``settings.cabinet_subscription_open_to_all``:

- **True** (Phase-1 default): all sellers can use Cabinet features.
  No DB hit; constant-time True. Test-period UX, per DECISION_MATRIX
  D4-Q1.
- **False** (post-test): real subscription lookup against the existing
  ``subscriptions`` table (Block C). Returns True iff the user has an
  ACTIVE row of the requested type.

The flip is one config flag — no migration, no code change, no
restart. The helper is the only place that decides; callers don't
know about the test-period override.
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Subscription, SubscriptionStatus, SubscriptionType

logger = logging.getLogger(__name__)


async def check_active_subscription(
    db: AsyncSession,
    user_id: UUID,
    sub_type: SubscriptionType = SubscriptionType.CABINET,
) -> bool:
    """Return True if ``user_id`` can use the requested subscription tier.

    Treats ``SubscriptionStatus.ACTIVE`` and ``GRACE`` as access-granted;
    PAUSED / CANCELLED / EXPIRED count as denied. Callers should treat
    a False return as "show subscription paywall" rather than 5xx.
    """
    if settings.cabinet_subscription_open_to_all:
        return True

    row = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.type == sub_type,
            Subscription.status.in_(
                (SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE)
            ),
        )
    )
    return row.scalar_one_or_none() is not None


async def get_active_subscription(
    db: AsyncSession,
    user_id: UUID,
    sub_type: SubscriptionType = SubscriptionType.CABINET,
) -> Optional[Subscription]:
    """Return the active subscription row, if any. Useful for cabinet
    UI that needs to render renewal dates etc."""
    if settings.cabinet_subscription_open_to_all:
        # In test-period mode we have no row to return; callers that
        # care about renewal dates should treat this as "n/a".
        return None
    row = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user_id,
            Subscription.type == sub_type,
            Subscription.status.in_(
                (SubscriptionStatus.ACTIVE, SubscriptionStatus.GRACE)
            ),
        )
    )
    return row.scalar_one_or_none()
