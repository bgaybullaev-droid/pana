"""Tests for admin API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Listing, ModerationStatus, User, UserApprovalStatus, UserRole

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestAdminDashboard:
    """GET /api/v1/admin/dashboard"""

    async def test_dashboard_stats(self, client: AsyncClient, admin_headers):
        resp = await client.get("/api/v1/admin/dashboard", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "total_listings" in data

    async def test_dashboard_non_admin(self, client: AsyncClient, user_headers):
        resp = await client.get("/api/v1/admin/dashboard", headers=user_headers)
        assert resp.status_code == 403

    async def test_dashboard_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 401


class TestAdminListUsers:
    """GET /api/v1/admin/users"""

    async def test_list_users(self, client: AsyncClient, admin_headers, test_user):
        resp = await client.get("/api/v1/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_users_filter_approval(self, client: AsyncClient, admin_headers):
        resp = await client.get(
            "/api/v1/admin/users",
            params={"approval_status": "approved"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    async def test_list_users_filter_role(self, client: AsyncClient, admin_headers):
        resp = await client.get(
            "/api/v1/admin/users", params={"role": "seller"}, headers=admin_headers
        )
        assert resp.status_code == 200

    async def test_list_users_search(
        self, client: AsyncClient, admin_headers, test_user
    ):
        resp = await client.get(
            "/api/v1/admin/users", params={"q": "Test"}, headers=admin_headers
        )
        assert resp.status_code == 200

    async def test_list_users_non_admin(self, client: AsyncClient, user_headers):
        resp = await client.get("/api/v1/admin/users", headers=user_headers)
        assert resp.status_code == 403


class TestAdminGetUser:
    """GET /api/v1/admin/users/{user_id}"""

    async def test_get_user_detail(self, client: AsyncClient, admin_headers, test_user):
        resp = await client.get(
            f"/api/v1/admin/users/{test_user.id}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == str(test_user.id)

    async def test_get_user_not_found(self, client: AsyncClient, admin_headers):
        resp = await client.get(f"/api/v1/admin/users/{uuid4()}", headers=admin_headers)
        assert resp.status_code == 404


class TestAdminApproveUser:
    """POST /api/v1/admin/users/{user_id}/approve"""

    async def test_approve_pending_user(
        self, client: AsyncClient, admin_headers, db_session
    ):
        from tests.conftest import auth_headers as make_auth_headers

        # Create pending user
        pending = User(
            id=uuid4(),
            telegram_id=555555555,
            first_name="Pending",
            username="pending",
            role=UserRole.SELLER,
            approval_status=UserApprovalStatus.PENDING,
            auth_source="telegram",
        )
        db_session.add(pending)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/admin/users/{pending.id}/approve",
            json={"notes": "Looks good"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    async def test_approve_non_admin(
        self, client: AsyncClient, user_headers, test_user
    ):
        resp = await client.post(
            f"/api/v1/admin/users/{test_user.id}/approve", json={}, headers=user_headers
        )
        assert resp.status_code == 403


class TestAdminRejectUser:
    """POST /api/v1/admin/users/{user_id}/reject"""

    async def test_reject_user_with_reason(
        self, client: AsyncClient, admin_headers, db_session
    ):
        pending = User(
            id=uuid4(),
            telegram_id=666666666,
            first_name="Reject",
            username="reject",
            role=UserRole.SELLER,
            approval_status=UserApprovalStatus.PENDING,
            auth_source="telegram",
        )
        db_session.add(pending)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/admin/users/{pending.id}/reject",
            json={"notes": "Incomplete profile"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    async def test_reject_without_reason(
        self, client: AsyncClient, admin_headers, test_user
    ):
        resp = await client.post(
            f"/api/v1/admin/users/{test_user.id}/reject",
            json={},
            headers=admin_headers,
        )
        assert resp.status_code in [200, 422]


class TestAdminListings:
    """GET /api/v1/admin/listings"""

    async def test_list_admin_listings(
        self, client: AsyncClient, admin_headers, test_listing
    ):
        resp = await client.get("/api/v1/admin/listings", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_filter_by_moderation_status(
        self, client: AsyncClient, admin_headers
    ):
        resp = await client.get(
            "/api/v1/admin/listings",
            params={"moderation_status": "approved"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    async def test_filter_by_source_type(self, client: AsyncClient, admin_headers):
        resp = await client.get(
            "/api/v1/admin/listings",
            params={"source_type": "manual"},
            headers=admin_headers,
        )
        assert resp.status_code == 200


class TestAdminApproveListing:
    """POST /api/v1/admin/listings/{listing_id}/approve"""

    async def test_approve_listing(
        self, client: AsyncClient, admin_headers, test_listing
    ):
        resp = await client.post(
            f"/api/v1/admin/listings/{test_listing.id}/approve",
            json={"notes": "Approved"},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    async def test_approve_listing_non_admin(
        self, client: AsyncClient, user_headers, test_listing
    ):
        resp = await client.post(
            f"/api/v1/admin/listings/{test_listing.id}/approve",
            json={},
            headers=user_headers,
        )
        assert resp.status_code == 403


class TestAdminRejectListing:
    """POST /api/v1/admin/listings/{listing_id}/reject"""

    async def test_reject_listing_with_reason(
        self, client: AsyncClient, admin_headers, test_listing
    ):
        resp = await client.post(
            f"/api/v1/admin/listings/{test_listing.id}/reject",
            json={"notes": "Low quality images"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
