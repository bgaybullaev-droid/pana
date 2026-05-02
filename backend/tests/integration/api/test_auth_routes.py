"""
Comprehensive tests for auth endpoints (/api/v1/auth/*).

Covers: /me, /buyer-phone, /admin-login, /refresh, /logout,
        /dev-login, /seller-otp, /seller-bot-info, /telegram.
"""

import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from unittest.mock import AsyncMock, patch
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token
from app.db.models import Seller, User, UserApprovalStatus, UserRole


def _build_signed_init_data(
    bot_token: str,
    telegram_id: int,
    first_name: str = "Ivan",
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    photo_url: Optional[str] = None,
    language_code: Optional[str] = "ru",
    auth_date: Optional[int] = None,
) -> str:
    """Craft a Telegram WebApp initData string with a valid HMAC signature.

    Mirrors the algorithm in app.core.security.verify_telegram_init_data so tests
    can exercise the /auth/telegram endpoint without a real Telegram client.
    """
    user_payload: Dict[str, object] = {"id": telegram_id, "first_name": first_name}
    if last_name:
        user_payload["last_name"] = last_name
    if username:
        user_payload["username"] = username
    if photo_url:
        user_payload["photo_url"] = photo_url
    if language_code:
        user_payload["language_code"] = language_code

    fields = {
        "auth_date": str(auth_date or int(time.time())),
        "user": json.dumps(user_payload, separators=(",", ":")),
    }

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()
    fields["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(fields)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.auth,
    pytest.mark.asyncio,
]

API = "/api/v1/auth"


# ============================================================================
# 1. GET /api/v1/auth/me
# ============================================================================


class TestGetMe:
    """Tests for the GET /me endpoint."""

    async def test_get_me_authenticated(
        self,
        client: AsyncClient,
        test_user: User,
        user_headers: Dict[str, str],
    ):
        """Valid token returns current user data."""
        resp = await client.get(f"{API}/me", headers=user_headers)
        assert resp.status_code == 200

        data = resp.json()
        assert data["user_id"] == str(test_user.id)
        assert data["first_name"] == test_user.first_name
        assert data["telegram_id"] == test_user.telegram_id
        assert data["role"] == "user"
        assert data["is_seller"] is False
        assert data["approval_status"] == "approved"

    async def test_get_me_no_token(self, client: AsyncClient):
        """Missing token returns 401."""
        resp = await client.get(f"{API}/me")
        assert resp.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        """Garbage token returns 401."""
        headers = {"Authorization": "Bearer this.is.not.a.valid.jwt"}
        resp = await client.get(f"{API}/me", headers=headers)
        assert resp.status_code == 401

    async def test_get_me_expired_token(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Expired token returns 401."""
        expired_token = create_access_token(
            {"sub": str(test_user.id)},
            expires_delta=timedelta(seconds=-1),
        )
        headers = {"Authorization": f"Bearer {expired_token}"}
        resp = await client.get(f"{API}/me", headers=headers)
        assert resp.status_code == 401

    async def test_get_me_deleted_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        user_headers: Dict[str, str],
    ):
        """Soft-deleted user returns 401 even with a valid token."""
        test_user.deleted_at = datetime.utcnow()
        await db_session.flush()

        resp = await client.get(f"{API}/me", headers=user_headers)
        assert resp.status_code == 401


# ============================================================================
# 2. POST /api/v1/auth/buyer-phone
# ============================================================================


class TestBuyerPhone:
    """Tests for the POST /buyer-phone endpoint."""

    @patch("app.api.v1.auth.get_redis")
    async def test_buyer_phone_login_new_user(
        self,
        mock_redis,
        client: AsyncClient,
    ):
        """New phone number creates a user and returns tokens."""
        mock_redis.return_value = AsyncMock(
            setex=AsyncMock(),
            get=AsyncMock(return_value=None),
        )

        payload = {
            "phone": "+998991112233",
            "first_name": "Buyer",
            "last_name": "New",
        }
        resp = await client.post(f"{API}/buyer-phone", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["first_name"] == "Buyer"
        assert data["last_name"] == "New"
        assert data["role"] == "user"
        assert data["scope"] == "buyer"
        assert data["phone"] == "+998991112233"

    @patch("app.api.v1.auth.get_redis")
    async def test_buyer_phone_login_existing_user(
        self,
        mock_redis,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Existing phone user logs in and name is updated."""
        mock_redis.return_value = AsyncMock(
            setex=AsyncMock(),
            get=AsyncMock(return_value=None),
        )

        # Create a user with known phone
        user = User(
            id=uuid4(),
            first_name="Old",
            last_name="Name",
            phone="+998997776655",
            role=UserRole.USER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="buyer_phone",
        )
        db_session.add(user)
        await db_session.flush()

        payload = {
            "phone": "+998997776655",
            "first_name": "Updated",
            "last_name": "Name2",
        }
        resp = await client.post(f"{API}/buyer-phone", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert data["user_id"] == str(user.id)
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name2"

    async def test_buyer_phone_login_missing_fields(self, client: AsyncClient):
        """Missing required fields returns 422."""
        # Missing first_name
        resp = await client.post(
            f"{API}/buyer-phone",
            json={"phone": "+998991112233"},
        )
        assert resp.status_code == 422

    async def test_buyer_phone_login_invalid_phone(self, client: AsyncClient):
        """Invalid phone format returns 422."""
        resp = await client.post(
            f"{API}/buyer-phone",
            json={"phone": "123", "first_name": "X"},
        )
        assert resp.status_code == 422


# ============================================================================
# 3. POST /api/v1/auth/admin-login
# ============================================================================


class TestAdminLogin:
    """Tests for the POST /admin-login endpoint."""

    @patch("app.api.v1.auth.get_redis")
    async def test_admin_login_success(
        self,
        mock_redis,
        client: AsyncClient,
    ):
        """Valid admin credentials return tokens and admin user."""
        mock_redis.return_value = AsyncMock(
            setex=AsyncMock(),
            get=AsyncMock(return_value=None),
        )

        settings = get_settings()
        payload = {
            "username": settings.admin_username,
            "password": settings.admin_password,
        }
        resp = await client.post(f"{API}/admin-login", json=payload)
        assert resp.status_code == 200

        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["role"] == "admin"
        assert data["scope"] == "admin"
        assert data["is_seller"] is True  # admin counts as seller

    async def test_admin_login_wrong_password(self, client: AsyncClient):
        """Wrong password returns 401."""
        settings = get_settings()
        resp = await client.post(
            f"{API}/admin-login",
            json={"username": settings.admin_username, "password": "wrong_pw"},
        )
        assert resp.status_code == 401

    async def test_admin_login_wrong_username(self, client: AsyncClient):
        """Wrong username returns 401."""
        resp = await client.post(
            f"{API}/admin-login",
            json={"username": "nonexistent", "password": "whatever1"},
        )
        assert resp.status_code == 401

    async def test_admin_login_empty_credentials(self, client: AsyncClient):
        """Empty/missing credentials returns 422."""
        resp = await client.post(f"{API}/admin-login", json={})
        assert resp.status_code == 422


# ============================================================================
# 4. POST /api/v1/auth/refresh
# ============================================================================


class TestRefreshToken:
    """Tests for the POST /refresh endpoint."""

    @patch("app.api.v1.auth.get_redis")
    async def test_refresh_token_success(
        self,
        mock_redis,
        client: AsyncClient,
        test_user: User,
    ):
        """Valid refresh token returns a new token pair."""
        mock_redis.return_value = AsyncMock(
            setex=AsyncMock(),
            get=AsyncMock(return_value=None),
        )

        refresh = create_refresh_token({"sub": str(test_user.id), "scope": "buyer"})
        resp = await client.post(
            f"{API}/refresh",
            json={"refresh_token": refresh},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["user_id"] == str(test_user.id)
        assert data["scope"] == "buyer"

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Random string as refresh token returns 401."""
        resp = await client.post(
            f"{API}/refresh",
            json={"refresh_token": "not.a.real.token"},
        )
        assert resp.status_code == 401

    async def test_refresh_token_access_token_used(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """Using an access token as refresh token returns 401 (wrong type)."""
        access = create_access_token({"sub": str(test_user.id), "scope": "buyer"})
        resp = await client.post(
            f"{API}/refresh",
            json={"refresh_token": access},
        )
        assert resp.status_code == 401

    async def test_refresh_token_missing(self, client: AsyncClient):
        """No refresh token in body or cookie returns 401."""
        resp = await client.post(f"{API}/refresh", json={})
        # The body schema has refresh_token as required; Pydantic may return 422,
        # but if body=None is allowed the endpoint itself returns 401.
        assert resp.status_code in (401, 422)


# ============================================================================
# 5. POST /api/v1/auth/logout
# ============================================================================


class TestLogout:
    """Tests for the POST /logout endpoint."""

    async def test_logout_success(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
    ):
        """Authenticated logout clears cookies and returns 200."""
        resp = await client.post(f"{API}/logout", headers=user_headers)
        assert resp.status_code == 200
        assert resp.json()["message"] == "Successfully logged out"

        # Cookies should be deleted (max-age=0 or Set-Cookie with expiry)
        set_cookie_headers = resp.headers.get_list("set-cookie")
        cookie_text = " ".join(set_cookie_headers)
        assert "access_token" in cookie_text
        assert "refresh_token" in cookie_text

    async def test_logout_unauthenticated(self, client: AsyncClient):
        """Logout without a token is idempotent and still returns 200."""
        resp = await client.post(f"{API}/logout")
        assert resp.status_code == 200


# ============================================================================
# 6. POST /api/v1/auth/dev-login
# ============================================================================


class TestDevLogin:
    """Tests for the POST /dev-login endpoint."""

    @patch("app.api.v1.auth.get_redis")
    async def test_dev_login_in_test_env(
        self,
        mock_redis,
        client: AsyncClient,
    ):
        """Dev login creates/returns a dev user in non-production env."""
        # We don't need Redis for dev-login (it doesn't call _generate_and_store_tokens)
        # but the endpoint creates tokens directly. No Redis needed.
        resp = await client.post(f"{API}/dev-login")
        assert resp.status_code == 200

        data = resp.json()
        assert data["first_name"] == "Dev"
        assert data["last_name"] == "User"
        assert data["role"] == "user"

    @patch("app.api.v1.auth.get_redis")
    async def test_dev_login_returns_tokens(
        self,
        mock_redis,
        client: AsyncClient,
    ):
        """Dev login response includes access and refresh tokens."""
        resp = await client.post(f"{API}/dev-login")
        assert resp.status_code == 200

        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["expires_in"] > 0


# ============================================================================
# 7. POST /api/v1/auth/seller-otp
# ============================================================================


class TestSellerOTP:
    """Tests for the POST /seller-otp endpoint."""

    async def test_request_seller_otp_no_phone(self, client: AsyncClient):
        """Missing phone field returns 422 (Pydantic validation)."""
        resp = await client.post(f"{API}/seller-otp", json={})
        assert resp.status_code == 422

    @patch("app.api.v1.auth.get_redis")
    async def test_request_seller_otp_phone_not_found(
        self,
        mock_redis,
        client: AsyncClient,
    ):
        """Phone not registered returns 400."""
        mock_redis.return_value = AsyncMock(
            get=AsyncMock(return_value=None),
        )

        resp = await client.post(
            f"{API}/seller-otp",
            json={"phone": "+998900000000"},
        )
        assert resp.status_code == 400

    @patch("app.api.v1.auth.get_redis")
    @patch("app.api.v1.auth.get_bot_instance", return_value=None)
    async def test_request_seller_otp_rate_limit(
        self,
        mock_bot,
        mock_redis,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller_user: User,
    ):
        """Fourth OTP request within the window is rejected (rate limit)."""
        call_count = 0
        rate_store: Dict[str, str] = {}

        async def mock_get(key):
            return rate_store.get(key)

        async def mock_setex(key, ttl, value):
            rate_store[key] = str(value)

        async def mock_incr(key):
            rate_store[key] = str(int(rate_store.get(key, "0")) + 1)

        async def mock_delete(key):
            rate_store.pop(key, None)

        redis_instance = AsyncMock()
        redis_instance.get = mock_get
        redis_instance.setex = mock_setex
        redis_instance.incr = mock_incr
        redis_instance.delete = mock_delete
        mock_redis.return_value = redis_instance

        phone = test_seller_user.phone  # "+998901234567"

        # First 3 requests should succeed
        for i in range(3):
            resp = await client.post(
                f"{API}/seller-otp",
                json={"phone": phone},
            )
            assert resp.status_code == 200, f"Request {i+1} failed: {resp.text}"

        # 4th request should be rate limited
        resp = await client.post(
            f"{API}/seller-otp",
            json={"phone": phone},
        )
        assert resp.status_code == 400
        assert (
            "много запросов" in resp.json()["detail"]["error"]["message"].lower()
            or "rate" in resp.json()["detail"]["error"]["message"].lower()
            or "Слишком" in resp.json()["detail"]["error"]["message"]
        )


# ============================================================================
# 8. GET /api/v1/auth/seller-bot-info
# ============================================================================


class TestSellerBotInfo:
    """Tests for the GET /seller-bot-info endpoint."""

    async def test_seller_bot_info(self, client: AsyncClient):
        """Returns bot username from settings."""
        resp = await client.get(f"{API}/seller-bot-info")
        assert resp.status_code == 200

        data = resp.json()
        assert "bot_username" in data
        settings = get_settings()
        assert data["bot_username"] == settings.telegram_bot_username


# ============================================================================
# 9. POST /api/v1/auth/telegram
# ============================================================================


class TestTelegramAuth:
    """Tests for the POST /telegram endpoint."""

    async def test_telegram_auth_invalid_data(self, client: AsyncClient):
        """Invalid initData returns 401."""
        resp = await client.post(
            f"{API}/telegram",
            json={"init_data": "auth_date=0&hash=invalidhashvalue&user={}"},
        )
        assert resp.status_code == 401

    async def test_telegram_auth_missing_data(self, client: AsyncClient):
        """Missing init_data field returns 422."""
        resp = await client.post(f"{API}/telegram", json={})
        assert resp.status_code == 422

    async def test_telegram_auth_new_user_creates_seller(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """First-time Mini App open creates a SELLER with a Seller row and seller-scoped tokens."""
        telegram_id = 555000001
        init_data = _build_signed_init_data(
            bot_token=get_settings().telegram_bot_token,
            telegram_id=telegram_id,
            first_name="Alisher",
            username="alisher_tg",
        )

        resp = await client.post(f"{API}/telegram", json={"init_data": init_data})
        assert resp.status_code == 200

        data = resp.json()
        assert data["telegram_id"] == telegram_id
        assert data["role"] == "seller"
        assert data["is_seller"] is True
        assert data["approval_status"] == "approved"
        assert data["auth_source"] == "telegram_webapp"
        assert data["scope"] == "seller"
        assert data["access_token"]
        assert data["refresh_token"]

        user = (
            await db_session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
        ).scalar_one()
        assert user.role == UserRole.SELLER
        assert user.approval_status == UserApprovalStatus.APPROVED

        seller = (
            await db_session.execute(select(Seller).where(Seller.user_id == user.id))
        ).scalar_one()
        assert seller.telegram_username == "alisher_tg"

    async def test_telegram_auth_promotes_legacy_user(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """A pre-change buyer (role=USER, no Seller row) is promoted to SELLER on re-auth."""
        telegram_id = 555000002
        legacy = User(
            id=uuid4(),
            telegram_id=telegram_id,
            first_name="Legacy",
            role=UserRole.USER,
            approval_status=UserApprovalStatus.PENDING,
            auth_source="telegram",
            onboarding_completed=False,
        )
        db_session.add(legacy)
        await db_session.flush()

        init_data = _build_signed_init_data(
            bot_token=get_settings().telegram_bot_token,
            telegram_id=telegram_id,
            first_name="Legacy",
        )
        resp = await client.post(f"{API}/telegram", json={"init_data": init_data})
        assert resp.status_code == 200

        data = resp.json()
        assert data["user_id"] == str(legacy.id)
        assert data["role"] == "seller"
        assert data["is_seller"] is True
        assert data["approval_status"] == "approved"
        assert data["scope"] == "seller"

        await db_session.refresh(legacy)
        assert legacy.role == UserRole.SELLER
        assert legacy.approval_status == UserApprovalStatus.APPROVED

        seller = (
            await db_session.execute(select(Seller).where(Seller.user_id == legacy.id))
        ).scalar_one()
        assert seller is not None

    async def test_telegram_auth_preserves_existing_seller(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Existing SELLER keeps their Seller profile (company_name, phone) untouched on re-auth."""
        telegram_id = 555000003
        user = User(
            id=uuid4(),
            telegram_id=telegram_id,
            first_name="OldName",
            phone="+998901112233",
            role=UserRole.SELLER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="seller_otp",
            onboarding_completed=True,
        )
        db_session.add(user)
        await db_session.flush()
        seller = Seller(
            id=uuid4(),
            user_id=user.id,
            company_name="Original Agency",
            phone="+998901112233",
        )
        db_session.add(seller)
        await db_session.flush()

        init_data = _build_signed_init_data(
            bot_token=get_settings().telegram_bot_token,
            telegram_id=telegram_id,
            first_name="NewName",
            username="newhandle",
        )
        resp = await client.post(f"{API}/telegram", json={"init_data": init_data})
        assert resp.status_code == 200

        data = resp.json()
        assert data["role"] == "seller"
        assert data["auth_source"] == "seller_otp"  # original source preserved
        assert data["phone"] == "+998901112233"

        await db_session.refresh(seller)
        assert seller.company_name == "Original Agency"
        assert seller.phone == "+998901112233"

    async def test_telegram_auth_handles_soft_deleted_collision(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """A soft-deleted row holding the telegram_id must not block a fresh signup."""
        telegram_id = 555000004
        ghost = User(
            id=uuid4(),
            telegram_id=telegram_id,
            first_name="Ghost",
            role=UserRole.USER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="telegram",
            deleted_at=datetime.utcnow(),
        )
        db_session.add(ghost)
        await db_session.flush()

        init_data = _build_signed_init_data(
            bot_token=get_settings().telegram_bot_token,
            telegram_id=telegram_id,
            first_name="Fresh",
        )
        resp = await client.post(f"{API}/telegram", json={"init_data": init_data})
        assert resp.status_code == 200

        data = resp.json()
        assert data["user_id"] != str(ghost.id)
        assert data["role"] == "seller"

        await db_session.refresh(ghost)
        assert ghost.telegram_id is None  # freed up

        live = (
            await db_session.execute(
                select(User).where(
                    User.telegram_id == telegram_id,
                    User.deleted_at.is_(None),
                )
            )
        ).scalar_one()
        assert str(live.id) == data["user_id"]
