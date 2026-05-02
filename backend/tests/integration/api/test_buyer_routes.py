"""Tests for buyer API endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestBuyerListings:
    """GET /api/v1/buyer/listings"""

    async def test_get_buyer_listings(self, client: AsyncClient, test_listing):
        resp = await client.get("/api/v1/buyer/listings")
        assert resp.status_code == 200

    async def test_buyer_listings_with_pascal_case_params(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.get(
            "/api/v1/buyer/listings",
            params={
                "PageSize": 10,
                "PageNumber": 1,
                "SortingName": 0,
            },
        )
        assert resp.status_code == 200

    async def test_buyer_listings_with_search(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/buyer/listings", params={"SearchTerm": "apartment"}
        )
        assert resp.status_code == 200

    async def test_buyer_listings_with_price_filter(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.get(
            "/api/v1/buyer/listings", params={"MinPrice": 10000, "MaxPrice": 100000}
        )
        assert resp.status_code == 200


class TestToggleLike:
    """POST /api/v1/buyer/listings/{listing_id}/like"""

    async def test_toggle_like(self, client: AsyncClient, user_headers, test_listing):
        resp = await client.post(
            f"/api/v1/buyer/listings/{test_listing.id}/like", headers=user_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "is_liked" in data

    async def test_toggle_like_unauthenticated(self, client: AsyncClient, test_listing):
        resp = await client.post(f"/api/v1/buyer/listings/{test_listing.id}/like")
        assert resp.status_code == 401
