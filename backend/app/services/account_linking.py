"""Account linking service for Telegram authentication."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.db.models import Seller, User

logger = logging.getLogger(__name__)


async def reserve_phone_for_user(
    db: AsyncSession,
    *,
    incoming_phone: str,
    target_user_id: Optional[UUID],
) -> None:
    """Hard-stop on active clash; free stale ``users.phone`` and
    ``sellers.phone`` for any other row holding the same phone.

    Caller MUST canonicalise ``incoming_phone`` first (E.164). Call
    before ``db.commit()`` in every login flow that sets ``User.phone``.

    Raises ``BadRequestException`` when an active (non-soft-deleted)
    user other than ``target_user_id`` already owns the phone — silently
    re-assigning across active users is unsafe.
    """
    # Active clash on users.phone → 400.
    active_q = select(User).where(
        User.phone == incoming_phone,
        User.deleted_at.is_(None),
    )
    if target_user_id is not None:
        active_q = active_q.where(User.id != target_user_id)
    active = (await db.execute(active_q)).scalar_one_or_none()
    if active is not None:
        raise BadRequestException("This phone is linked to another account.")

    # Free soft-deleted users.phone for the same number.
    stale_q = select(User).where(
        User.phone == incoming_phone,
        User.deleted_at.is_not(None),
    )
    if target_user_id is not None:
        stale_q = stale_q.where(User.id != target_user_id)
    for stale_user in (await db.execute(stale_q)).scalars().all():
        stale_user.phone = None

    # Free sellers.phone owned by anyone other than the target user.
    seller_q = select(Seller).where(Seller.phone == incoming_phone)
    if target_user_id is not None:
        seller_q = seller_q.where(Seller.user_id != target_user_id)
    for stale_seller in (await db.execute(seller_q)).scalars().all():
        stale_seller.phone = None

    await db.flush()


class AccountLinkingService:
    """Service for managing Telegram account linking."""

    async def find_user_by_identifiers(
        self,
        db: AsyncSession,
        telegram_id: Optional[int] = None,
    ) -> Optional[User]:
        """Find existing user by telegram_id."""
        if not telegram_id:
            return None

        result = await db.execute(
            select(User).where(
                User.telegram_id == telegram_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    def update_login_info(self, user: User) -> None:
        """Update last login information (call before commit)."""
        user.last_login_at = datetime.utcnow()


# Singleton instance
_account_linking_service: Optional[AccountLinkingService] = None


def get_account_linking_service() -> AccountLinkingService:
    """Get account linking service singleton."""
    global _account_linking_service
    if _account_linking_service is None:
        _account_linking_service = AccountLinkingService()
    return _account_linking_service
