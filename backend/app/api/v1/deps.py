"""API dependencies."""

from typing import Optional
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import verify_telegram_init_data, verify_token
from app.db.database import get_db
from app.db.models import Seller, User, UserApprovalStatus, UserRole

# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Get current authenticated user."""
    # Try to get token from Authorization header
    token = None
    if credentials:
        token = credentials.credentials

    # Or from cookies
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise UnauthorizedException("Missing authentication token")

    # Verify token
    payload = verify_token(token, "access")
    if not payload:
        raise UnauthorizedException("Invalid or expired token")

    # Get user from database
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Invalid token payload")

    result = await db.execute(
        select(User).where(User.id == UUID(user_id), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("User not found")

    # Account-switch defense. Telegram Mini App sends the active account's
    # signed initData in X-Telegram-Init-Data on every request. ONLY block
    # when verification SUCCEEDS and the header's telegram_id disagrees with
    # the cookie session — otherwise (stale auth_date, signature mismatch,
    # missing header, malformed) trust the cookie. This keeps long-idle
    # sessions usable while still catching real account switches.
    init_data = request.headers.get("X-Telegram-Init-Data")
    if init_data:
        tg_user_data = verify_telegram_init_data(
            init_data, settings.telegram_bot_token
        )
        if tg_user_data:
            header_telegram_id = tg_user_data.get("telegram_id")
            if (
                header_telegram_id is not None
                and user.telegram_id is not None
                and user.telegram_id != header_telegram_id
            ):
                raise UnauthorizedException(
                    "Session does not match active Telegram account"
                )

    # Store token scope on user object for downstream checks
    user._token_scope = payload.get("scope")

    # Check user approval status (skip for admins and when auto-approve is on)
    if not settings.auto_approve_users and user.role != UserRole.ADMIN:
        if user.approval_status == UserApprovalStatus.PENDING:
            raise ForbiddenException("Account pending approval")
        elif user.approval_status == UserApprovalStatus.REJECTED:
            raise ForbiddenException("Account has been rejected")

    return user


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise."""
    try:
        return await get_current_user(request, db, credentials)
    except UnauthorizedException:
        return None


async def get_current_seller(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Seller:
    """Get current authenticated seller."""
    if current_user.role not in [UserRole.SELLER, UserRole.ADMIN]:
        raise ForbiddenException("Seller access required")

    result = await db.execute(select(Seller).where(Seller.user_id == current_user.id))
    seller = result.scalar_one_or_none()

    if not seller:
        raise ForbiddenException("Seller profile not found")

    return seller


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current authenticated admin."""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException("Admin access required")
    # Validate token was issued with admin scope
    token_scope = getattr(current_user, "_token_scope", None)
    if token_scope and token_scope != "admin":
        raise ForbiddenException("Admin-scoped token required")
    return current_user
