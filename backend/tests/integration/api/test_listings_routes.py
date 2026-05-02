"""Tests for listings API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Currency,
    Listing,
    ListingImage,
    ListingStatus,
    ListingType,
    ModerationStatus,
    OLXListing,
    PropertyType,
    SourceType,
    TelegramListing,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestListListings:
    """GET /api/v1/listings"""

    async def test_list_listings_returns_paginated(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.get("/api/v1/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    async def test_list_listings_filter_by_type(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.get("/api/v1/listings", params={"type": "sell"})
        assert resp.status_code == 200

    async def test_list_listings_filter_by_property_type(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.get(
            "/api/v1/listings", params={"property_type": "apartment"}
        )
        assert resp.status_code == 200

    async def test_list_listings_filter_by_price_range(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.get(
            "/api/v1/listings", params={"price_min": 10000, "price_max": 100000}
        )
        assert resp.status_code == 200

    async def test_list_listings_search_by_query(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.get("/api/v1/listings", params={"q": "apartment"})
        assert resp.status_code == 200

    async def test_list_listings_pagination(self, client: AsyncClient, test_listing):
        resp = await client.get("/api/v1/listings", params={"page": 1, "per_page": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1

    async def test_list_listings_sort_by_price(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings", params={"sort_by": "price", "sort_order": "asc"}
        )
        assert resp.status_code == 200


class TestGetListing:
    """GET /api/v1/listings/{listing_id}"""

    async def test_get_listing_success(self, client: AsyncClient, test_listing):
        resp = await client.get(f"/api/v1/listings/{test_listing.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(test_listing.id)

    async def test_get_listing_not_found(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/listings/{uuid4()}")
        assert resp.status_code == 404

    async def test_get_listing_invalid_uuid(self, client: AsyncClient):
        resp = await client.get("/api/v1/listings/not-a-uuid")
        assert resp.status_code in [404, 422]


class TestResolveListing:
    """GET /api/v1/listings/resolve/{listing_id}"""

    async def test_resolve_main_listing(self, client: AsyncClient, test_listing):
        resp = await client.get(f"/api/v1/listings/resolve/{test_listing.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(test_listing.id)

    async def test_resolve_not_found(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/listings/resolve/{uuid4()}")
        assert resp.status_code == 404


class TestListingFeed:
    """GET /api/v1/listings/feed"""

    async def test_feed_returns_unified_listings(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.get("/api/v1/listings/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_feed_with_pagination(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"page": 1, "per_page": 10}
        )
        assert resp.status_code == 200

    async def test_feed_with_filters(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed",
            params={"type": "sell", "property_type": "apartment"},
        )
        assert resp.status_code == 200


class TestCreateListing:
    """POST /api/v1/listings"""

    async def test_create_listing_as_seller(
        self, client: AsyncClient, seller_headers, test_seller
    ):
        payload = {
            "title": "New Apartment",
            "description": "A great new apartment for sale",
            "type": "sell",
            "property_type": "apartment",
            "price": 75000,
            "currency": "usd",
            "rooms": 2,
            "area": 60.0,
            "region": "tashkent",
            "district": "mirzo_ulugbek",
            "phone": "+998901234567",
        }
        resp = await client.post(
            "/api/v1/listings", json=payload, headers=seller_headers
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Apartment"
        assert data["price"] == 75000

    async def test_create_listing_unauthenticated(self, client: AsyncClient):
        resp = await client.post("/api/v1/listings", json={"title": "Test"})
        assert resp.status_code in [401, 403]

    async def test_create_listing_as_regular_user(
        self, client: AsyncClient, user_headers
    ):
        resp = await client.post(
            "/api/v1/listings", json={"title": "Test"}, headers=user_headers
        )
        assert resp.status_code == 403

    async def test_create_listing_missing_required_fields(
        self, client: AsyncClient, seller_headers
    ):
        resp = await client.post("/api/v1/listings", json={}, headers=seller_headers)
        assert resp.status_code == 422


class TestUpdateListing:
    """PATCH /api/v1/listings/{listing_id}"""

    async def test_update_listing_as_owner(
        self, client: AsyncClient, seller_headers, test_listing
    ):
        resp = await client.patch(
            f"/api/v1/listings/{test_listing.id}",
            json={"price": 60000},
            headers=seller_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["price"] == 60000

    async def test_update_listing_unauthorized(self, client: AsyncClient, test_listing):
        resp = await client.patch(
            f"/api/v1/listings/{test_listing.id}", json={"price": 1}
        )
        assert resp.status_code in [401, 403]

    async def test_update_listing_not_found(self, client: AsyncClient, seller_headers):
        resp = await client.patch(
            f"/api/v1/listings/{uuid4()}",
            json={"price": 1},
            headers=seller_headers,
        )
        assert resp.status_code == 404


class TestDeleteListing:
    """DELETE /api/v1/listings/{listing_id}"""

    async def test_delete_listing_as_owner(
        self, client: AsyncClient, seller_headers, test_listing
    ):
        resp = await client.delete(
            f"/api/v1/listings/{test_listing.id}", headers=seller_headers
        )
        assert resp.status_code == 204

    async def test_delete_listing_unauthorized(self, client: AsyncClient, test_listing):
        resp = await client.delete(f"/api/v1/listings/{test_listing.id}")
        assert resp.status_code in [401, 403]

    async def test_delete_listing_not_found(self, client: AsyncClient, seller_headers):
        resp = await client.delete(
            f"/api/v1/listings/{uuid4()}", headers=seller_headers
        )
        assert resp.status_code == 404
