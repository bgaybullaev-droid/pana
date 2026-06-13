"""Tests for sellers API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BotChannelPost, Seller, User, UserRole

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestRegisterSeller:
    """POST /api/v1/sellers/register"""

    async def test_register_seller_success(
        self, client: AsyncClient, user_headers, test_user
    ):
        payload = {
            "company_name": "My Company",
            "phone": "+998991112233",
        }
        resp = await client.post(
            "/api/v1/sellers/register", json=payload, headers=user_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["company_name"] == "My Company"

    async def test_register_seller_unauthenticated(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/sellers/register",
            json={"company_name": "X", "phone": "+998991112233"},
        )
        assert resp.status_code == 401

    async def test_register_seller_already_registered(
        self, client: AsyncClient, seller_headers, test_seller
    ):
        resp = await client.post(
            "/api/v1/sellers/register",
            json={"company_name": "X", "phone": "+998991112233"},
            headers=seller_headers,
        )
        assert resp.status_code in [400, 409]

    async def test_register_seller_missing_fields(
        self, client: AsyncClient, user_headers
    ):
        resp = await client.post(
            "/api/v1/sellers/register", json={}, headers=user_headers
        )
        assert resp.status_code == 422


class TestGetSellerProfile:
    """GET /api/v1/sellers/me"""

    async def test_get_profile_success(
        self, client: AsyncClient, seller_headers, test_seller
    ):
        resp = await client.get("/api/v1/sellers/me", headers=seller_headers)
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "Test Company"

    async def test_get_profile_not_seller(self, client: AsyncClient, user_headers):
        resp = await client.get("/api/v1/sellers/me", headers=user_headers)
        assert resp.status_code == 403


class TestUpdateSellerProfile:
    """PATCH /api/v1/sellers/me"""

    async def test_update_profile_success(
        self, client: AsyncClient, seller_headers, test_seller
    ):
        resp = await client.patch(
            "/api/v1/sellers/me",
            json={"company_name": "Updated Company"},
            headers=seller_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "Updated Company"

    async def test_update_profile_unauthenticated(self, client: AsyncClient):
        resp = await client.patch("/api/v1/sellers/me", json={"company_name": "X"})
        assert resp.status_code == 401


class TestGetSellerListings:
    """GET /api/v1/sellers/me/listings"""

    async def test_get_seller_listings(
        self, client: AsyncClient, seller_headers, test_listing
    ):
        resp = await client.get("/api/v1/sellers/me/listings", headers=seller_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_get_seller_listings_with_status_filter(
        self, client: AsyncClient, seller_headers, test_listing
    ):
        resp = await client.get(
            "/api/v1/sellers/me/listings",
            params={"status": "active"},
            headers=seller_headers,
        )
        assert resp.status_code == 200


class TestSellerListingsAutopostOverlay:
    """GET /api/v1/sellers/me/listings — Block D D4 autopost overlay."""

    async def test_autopost_fields_default_when_no_post(
        self, client: AsyncClient, seller_headers, test_listing
    ):
        resp = await client.get(
            "/api/v1/sellers/me/listings", headers=seller_headers
        )
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["autopost_post_id"] is None
        assert item["autopost_is_stale"] is False

    async def test_stale_when_listing_edited_after_post(
        self,
        client: AsyncClient,
        seller_headers,
        test_seller,
        test_listing,
        db_session: AsyncSession,
    ):
        # The post captured an older version than the listing now carries.
        test_listing.version = 2
        db_session.add(
            BotChannelPost(
                listing_id=test_listing.id,
                seller_id=test_seller.id,
                channel_id=-1001234567890,
                message_id=42,
                last_listing_version=1,
                status="live",
            )
        )
        await db_session.flush()

        resp = await client.get(
            "/api/v1/sellers/me/listings", headers=seller_headers
        )
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["autopost_is_stale"] is True
        assert item["autopost_post_id"] is not None

    async def test_not_stale_when_post_in_sync(
        self,
        client: AsyncClient,
        seller_headers,
        test_seller,
        test_listing,
        db_session: AsyncSession,
    ):
        db_session.add(
            BotChannelPost(
                listing_id=test_listing.id,
                seller_id=test_seller.id,
                channel_id=-1001234567890,
                message_id=43,
                last_listing_version=test_listing.version,
                status="live",
            )
        )
        await db_session.flush()

        resp = await client.get(
            "/api/v1/sellers/me/listings", headers=seller_headers
        )
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["autopost_is_stale"] is False
        assert item["autopost_post_id"] is not None

    async def test_non_live_post_is_ignored(
        self,
        client: AsyncClient,
        seller_headers,
        test_seller,
        test_listing,
        db_session: AsyncSession,
    ):
        # Only status="live" posts count; a deleted-marker row must not
        # surface an autopost_post_id.
        test_listing.version = 5
        db_session.add(
            BotChannelPost(
                listing_id=test_listing.id,
                seller_id=test_seller.id,
                channel_id=-1001234567890,
                message_id=44,
                last_listing_version=1,
                status="deleted",
            )
        )
        await db_session.flush()

        resp = await client.get(
            "/api/v1/sellers/me/listings", headers=seller_headers
        )
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["autopost_post_id"] is None
        assert item["autopost_is_stale"] is False


class TestSellerPublicProfile:
    """GET /api/v1/sellers/{seller_id}"""

    async def test_get_public_profile(self, client: AsyncClient, test_seller):
        resp = await client.get(f"/api/v1/sellers/{test_seller.id}")
        assert resp.status_code == 200

    async def test_get_public_profile_not_found(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/sellers/{uuid4()}")
        assert resp.status_code == 404


class TestSellerPublicListings:
    """GET /api/v1/sellers/{seller_id}/listings"""

    async def test_get_public_listings(
        self, client: AsyncClient, test_seller, test_listing
    ):
        resp = await client.get(f"/api/v1/sellers/{test_seller.id}/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data


class TestSellerCrawledStats:
    """GET /api/v1/sellers/me/crawled/stats"""

    async def test_get_crawled_stats(self, client: AsyncClient, seller_headers):
        resp = await client.get(
            "/api/v1/sellers/me/crawled/stats", headers=seller_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "olx_count" in data
        assert "telegram_count" in data
