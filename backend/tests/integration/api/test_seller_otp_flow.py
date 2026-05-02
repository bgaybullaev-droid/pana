"""
End-to-end tests for the seller OTP flow (/api/v1/auth/seller-otp*).

Covers: OTP request (auto-create user), OTP verify (issue tokens,
promote role, create seller), wrong code, expired code, max attempts,
and validation errors.
"""

from typing import Dict
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Seller, User, UserApprovalStatus, UserRole

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]

API = "/api/v1/auth"


# ============================================================================
# Helpers
# ============================================================================


def _make_redis_mock(store: Dict[str, str] | None = None):
    """Build a mock Redis instance backed by an in-memory dict."""
    if store is None:
        store = {}

    async def mock_get(key):
        return store.get(key)

    async def mock_setex(key, _ttl, value):
        store[key] = str(value)

    async def mock_incr(key):
        store[key] = str(int(store.get(key, "0")) + 1)

    async def mock_delete(key):
        store.pop(key, None)

    redis_instance = AsyncMock()
    redis_instance.get = mock_get
    redis_instance.setex = mock_setex
    redis_instance.incr = mock_incr
    redis_instance.delete = mock_delete
    return redis_instance, store


# ============================================================================
# 1. Full OTP flow: request → verify → seller auto-created
# ============================================================================


class TestSellerOTPFlow:
    """End-to-end OTP flow: request → verify → seller auto-created."""

    @patch("app.api.v1.auth.get_bot_instance", return_value=None)
    @patch("app.api.v1.auth.get_redis")
    async def test_otp_request_creates_user_if_not_exists(
        self,
        mock_redis,
        _mock_bot,
        client: AsyncClient,
    ):
        """POST /seller-otp with a new phone auto-creates the user and returns expires_in."""
        redis_instance, _ = _make_redis_mock()
        mock_redis.return_value = redis_instance

        resp = await client.post(
            f"{API}/seller-otp",
            json={"phone": "+998909999888"},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert "expires_in" in data
        assert data["expires_in"] > 0

    @patch("app.api.v1.auth.get_redis")
    async def test_otp_verify_success_issues_tokens(
        self,
        mock_redis,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Correct OTP issues tokens, promotes role to SELLER, creates Seller profile."""
        phone = "+998908887766"
        phone_suffix = "908887766"

        # Pre-create user with this phone (simulates prior OTP request)
        user = User(
            id=uuid4(),
            first_name=f"Seller {phone_suffix[-4:]}",
            phone=phone,
            role=UserRole.USER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="seller_otp",
        )
        db_session.add(user)
        await db_session.flush()

        # Seed the OTP in mock Redis
        otp_code = "654321"
        store = {
            f"seller_otp:{phone_suffix}": otp_code,
        }
        redis_instance, _ = _make_redis_mock(store)
        mock_redis.return_value = redis_instance

        resp = await client.post(
            f"{API}/seller-otp/verify",
            json={"phone": phone, "otp_code": otp_code},
        )
        assert resp.status_code == 200

        data = resp.json()
        assert data["access_token"]
        assert data["refresh_token"]
        assert data["scope"] == "seller"

        # Verify user was promoted to SELLER
        await db_session.refresh(user)
        assert user.role == UserRole.SELLER

        # Verify seller profile was auto-created
        seller_result = await db_session.execute(
            select(Seller).where(Seller.user_id == user.id)
        )
        seller = seller_result.scalar_one_or_none()
        assert seller is not None

    @patch("app.api.v1.auth.get_redis")
    async def test_otp_verify_wrong_code(
        self,
        mock_redis,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Wrong OTP code returns 400."""
        phone = "+998907776655"
        phone_suffix = "907776655"

        user = User(
            id=uuid4(),
            first_name="WrongCode",
            phone=phone,
            role=UserRole.USER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="seller_otp",
        )
        db_session.add(user)
        await db_session.flush()

        store = {
            f"seller_otp:{phone_suffix}": "123456",
        }
        redis_instance, _ = _make_redis_mock(store)
        mock_redis.return_value = redis_instance

        resp = await client.post(
            f"{API}/seller-otp/verify",
            json={"phone": phone, "otp_code": "000000"},
        )
        assert resp.status_code == 400

    @patch("app.api.v1.auth.get_redis")
    async def test_otp_verify_expired(
        self,
        mock_redis,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Expired (missing) OTP returns 400."""
        phone = "+998906665544"

        user = User(
            id=uuid4(),
            first_name="Expired",
            phone=phone,
            role=UserRole.USER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="seller_otp",
        )
        db_session.add(user)
        await db_session.flush()

        # Empty store — OTP has expired / never stored
        redis_instance, _ = _make_redis_mock()
        mock_redis.return_value = redis_instance

        resp = await client.post(
            f"{API}/seller-otp/verify",
            json={"phone": phone, "otp_code": "123456"},
        )
        assert resp.status_code == 400

    @patch("app.api.v1.auth.get_redis")
    async def test_otp_verify_max_attempts(
        self,
        mock_redis,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        """OTP verification with max attempts already reached returns 400."""
        phone = "+998905554433"
        phone_suffix = "905554433"

        user = User(
            id=uuid4(),
            first_name="MaxAttempts",
            phone=phone,
            role=UserRole.USER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="seller_otp",
        )
        db_session.add(user)
        await db_session.flush()

        # OTP exists but attempts already at max (3)
        store = {
            f"seller_otp:{phone_suffix}": "123456",
            f"seller_otp_attempts:{phone_suffix}": "3",
        }
        redis_instance, _ = _make_redis_mock(store)
        mock_redis.return_value = redis_instance

        resp = await client.post(
            f"{API}/seller-otp/verify",
            json={"phone": phone, "otp_code": "123456"},
        )
        assert resp.status_code == 400
        msg = resp.json()["detail"]["error"]["message"].lower()
        assert "попыт" in msg or "attempts" in msg or "превышено" in msg


# ============================================================================
# 2. Validation errors
# ============================================================================


class TestSellerOTPValidation:
    """Request-level validation for OTP endpoints."""

    async def test_otp_request_missing_phone(self, client: AsyncClient):
        """Missing phone field returns 422."""
        resp = await client.post(f"{API}/seller-otp", json={})
        assert resp.status_code == 422

    async def test_otp_verify_missing_fields(self, client: AsyncClient):
        """Missing phone or otp_code returns 422."""
        # Missing otp_code
        resp = await client.post(
            f"{API}/seller-otp/verify",
            json={"phone": "+998901234567"},
        )
        assert resp.status_code == 422

        # Missing phone
        resp = await client.post(
            f"{API}/seller-otp/verify",
            json={"otp_code": "123456"},
        )
        assert resp.status_code == 422

        # Empty body
        resp = await client.post(f"{API}/seller-otp/verify", json={})
        assert resp.status_code == 422
