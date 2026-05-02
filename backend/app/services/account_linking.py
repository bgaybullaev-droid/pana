"""Account linking service for Telegram authentication."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User

logger = logging.getLogger(__name__)


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
