"""
Tests for role-based access control across all protected endpoints.

Covers: listing CRUD permissions, admin endpoint permissions,
favorites permissions, and seller endpoint permissions.
"""

from typing import Dict
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Listing, Seller, User, UserApprovalStatus, UserRole
from tests.conftest import seller_auth_headers

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ============================================================================
# Helpers
# ============================================================================


LISTING_PAYLOAD = {
    "title": "Permission Test Apartment",
    "description": "Testing permissions",
    "type": "sell",
    "property_type": "apartment",
    "price": 80000,
    "currency": "usd",
    "rooms": 2,
    "area": 55.0,
    "region": "tashkent",
    "district": "mirzo_ulugbek",
    "phone": "+998901234567",
}


# ============================================================================
# 1. Listing permissions
# ============================================================================


class TestListingPermissions:
    """CRUD permission checks for /api/v1/listings."""

    async def test_create_listing_buyer_forbidden(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
    ):
        """Regular buyer cannot create a listing."""
        resp = await client.post(
            "/api/v1/listings",
            json=LISTING_PAYLOAD,
            headers=user_headers,
        )
        assert resp.status_code == 403

    async def test_create_listing_seller_allowed(
        self,
        client: AsyncClient,
        seller_headers: Dict[str, str],
        test_seller: Seller,
    ):
        """Seller can create a listing."""
        resp = await client.post(
            "/api/v1/listings",
            json=LISTING_PAYLOAD,
            headers=seller_headers,
        )
        assert resp.status_code == 201

    async def test_create_listing_admin_allowed(
        self,
        client: AsyncClient,
        admin_headers: Dict[str, str],
        db_session: AsyncSession,
        test_admin_user: User,
    ):
        """Admin can create a listing (admin counts as seller)."""
        # Ensure admin has a seller profile
        seller = Seller(
            id=uuid4(),
            user_id=test_admin_user.id,
            company_name="Admin Seller",
            phone="+998900000001",
        )
        db_session.add(seller)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/listings",
            json=LISTING_PAYLOAD,
            headers=admin_headers,
        )
        assert resp.status_code == 201

    async def test_update_listing_non_owner_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_listing: Listing,
    ):
        """A different seller cannot update another seller's listing."""
        other_user = User(
            id=uuid4(),
            telegram_id=777777,
            first_name="Other",
            last_name="Seller",
            username="otherseller",
            phone="+998902222222",
            role=UserRole.SELLER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="olx_phone",
            onboarding_completed=True,
        )
        db_session.add(other_user)
        other_seller = Seller(
            id=uuid4(),
            user_id=other_user.id,
            company_name="Other Company",
            phone="+998902222222",
        )
        db_session.add(other_seller)
        await db_session.flush()

        other_headers = seller_auth_headers(other_user)

        resp = await client.patch(
            f"/api/v1/listings/{test_listing.id}",
            json={"price": 99999},
            headers=other_headers,
        )
        assert resp.status_code == 403

    async def test_update_listing_admin_can_update_any(
        self,
        client: AsyncClient,
        admin_headers: Dict[str, str],
        test_listing: Listing,
    ):
        """Admin can update any listing regardless of ownership."""
        resp = await client.patch(
            f"/api/v1/listings/{test_listing.id}",
            json={"price": 42000},
            headers=admin_headers,
        )
        assert resp.status_code == 200

    async def test_delete_listing_non_owner_forbidden(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_listing: Listing,
    ):
        """A different seller cannot delete another seller's listing."""
        other_user = User(
            id=uuid4(),
            telegram_id=888888,
            first_name="Delete",
            last_name="Other",
            username="deleteother",
            phone="+998903333333",
            role=UserRole.SELLER,
            approval_status=UserApprovalStatus.APPROVED,
            auth_source="olx_phone",
            onboarding_completed=True,
        )
        db_session.add(other_user)
        other_seller = Seller(
            id=uuid4(),
            user_id=other_user.id,
            company_name="Delete Other Co",
            phone="+998903333333",
        )
        db_session.add(other_seller)
        await db_session.flush()

        other_headers = seller_auth_headers(other_user)

        resp = await client.delete(
            f"/api/v1/listings/{test_listing.id}",
            headers=other_headers,
        )
        assert resp.status_code == 403

    async def test_delete_listing_admin_can_delete_any(
        self,
        client: AsyncClient,
        admin_headers: Dict[str, str],
        test_listing: Listing,
    ):
        """Admin can delete any listing regardless of ownership."""
        resp = await client.delete(
            f"/api/v1/listings/{test_listing.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 204


# ============================================================================
# 2. Admin endpoint permissions
# ============================================================================


class TestAdminEndpointPermissions:
    """Access control for /api/v1/admin/* endpoints."""

    async def test_admin_dashboard_buyer_forbidden(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
    ):
        """Buyer cannot access admin dashboard."""
        resp = await client.get("/api/v1/admin/dashboard", headers=user_headers)
        assert resp.status_code == 403

    async def test_admin_dashboard_seller_forbidden(
        self,
        client: AsyncClient,
        seller_headers: Dict[str, str],
    ):
        """Seller cannot access admin dashboard."""
        resp = await client.get("/api/v1/admin/dashboard", headers=seller_headers)
        assert resp.status_code == 403

    async def test_admin_users_buyer_forbidden(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
    ):
        """Buyer cannot list admin users."""
        resp = await client.get("/api/v1/admin/users", headers=user_headers)
        assert resp.status_code == 403

    async def test_admin_approve_user_buyer_forbidden(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
        test_user: User,
    ):
        """Buyer cannot approve users."""
        resp = await client.post(
            f"/api/v1/admin/users/{test_user.id}/approve",
            json={},
            headers=user_headers,
        )
        assert resp.status_code == 403

    async def test_admin_listings_buyer_forbidden(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
    ):
        """Buyer cannot access admin listings."""
        resp = await client.get("/api/v1/admin/listings", headers=user_headers)
        assert resp.status_code == 403

    async def test_all_admin_endpoints_unauthenticated(
        self,
        client: AsyncClient,
        test_user: User,
    ):
        """All admin endpoints return 401 without authentication."""
        endpoints = [
            ("GET", "/api/v1/admin/dashboard"),
            ("GET", "/api/v1/admin/users"),
            ("GET", f"/api/v1/admin/users/{test_user.id}"),
            ("POST", f"/api/v1/admin/users/{test_user.id}/approve"),
            ("POST", f"/api/v1/admin/users/{test_user.id}/reject"),
            ("GET", "/api/v1/admin/listings"),
        ]
        for method, url in endpoints:
            if method == "GET":
                resp = await client.get(url)
            else:
                resp = await client.post(url, json={})
            assert (
                resp.status_code == 401
            ), f"{method} {url} returned {resp.status_code}, expected 401"


# ============================================================================
# 3. Favorites permissions
# ============================================================================


class TestFavoritesPermissions:
    """Access control for /api/v1/favorites endpoints."""

    async def test_add_favorite_unauthenticated(
        self,
        client: AsyncClient,
        test_listing: Listing,
    ):
        """Unauthenticated user cannot add favorite."""
        resp = await client.post(f"/api/v1/favorites/{test_listing.id}")
        assert resp.status_code == 401

    async def test_get_favorites_unauthenticated(self, client: AsyncClient):
        """Unauthenticated user cannot list favorites."""
        resp = await client.get("/api/v1/favorites")
        assert resp.status_code == 401

    async def test_add_favorite_authenticated(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
        test_listing: Listing,
    ):
        """Authenticated buyer can add a favorite."""
        resp = await client.post(
            f"/api/v1/favorites/{test_listing.id}",
            headers=user_headers,
        )
        assert resp.status_code == 201


# ============================================================================
# 4. Seller endpoint permissions
# ============================================================================


class TestSellerEndpointPermissions:
    """Access control for /api/v1/sellers/me* endpoints."""

    async def test_seller_me_buyer_forbidden(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
    ):
        """Buyer cannot access seller profile."""
        resp = await client.get("/api/v1/sellers/me", headers=user_headers)
        assert resp.status_code == 403

    async def test_seller_listings_buyer_forbidden(
        self,
        client: AsyncClient,
        user_headers: Dict[str, str],
    ):
        """Buyer cannot list seller's own listings."""
        resp = await client.get("/api/v1/sellers/me/listings", headers=user_headers)
        assert resp.status_code == 403

    async def test_seller_me_seller_allowed(
        self,
        client: AsyncClient,
        seller_headers: Dict[str, str],
        test_seller: Seller,
    ):
        """Seller can access their own profile."""
        resp = await client.get("/api/v1/sellers/me", headers=seller_headers)
        assert resp.status_code == 200
