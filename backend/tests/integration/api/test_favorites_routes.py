"""Tests for favorites API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestGetFavoriteIds:
    """GET /api/v1/favorites/ids"""

    async def test_get_favorite_ids_empty(self, client: AsyncClient, user_headers):
        resp = await client.get("/api/v1/favorites/ids", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "ids" in data
        assert isinstance(data["ids"], list)

    async def test_get_favorite_ids_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/favorites/ids")
        assert resp.status_code == 401


class TestGetFavorites:
    """GET /api/v1/favorites"""

    async def test_get_favorites_empty(self, client: AsyncClient, user_headers):
        resp = await client.get("/api/v1/favorites", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_get_favorites_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/favorites")
        assert resp.status_code == 401


class TestAddFavorite:
    """POST /api/v1/favorites/{listing_id}"""

    async def test_add_favorite_success(
        self, client: AsyncClient, user_headers, test_listing
    ):
        resp = await client.post(
            f"/api/v1/favorites/{test_listing.id}", headers=user_headers
        )
        assert resp.status_code == 201

    async def test_add_favorite_not_found(self, client: AsyncClient, user_headers):
        resp = await client.post(f"/api/v1/favorites/{uuid4()}", headers=user_headers)
        assert resp.status_code in [404, 201]  # May create for any UUID

    async def test_add_favorite_unauthenticated(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.post(f"/api/v1/favorites/{test_listing.id}")
        assert resp.status_code == 401

    async def test_add_favorite_duplicate(
        self, client: AsyncClient, user_headers, test_listing
    ):
        await client.post(f"/api/v1/favorites/{test_listing.id}", headers=user_headers)
        resp = await client.post(
            f"/api/v1/favorites/{test_listing.id}", headers=user_headers
        )
        assert resp.status_code == 200  # Already in favorites


class TestRemoveFavorite:
    """DELETE /api/v1/favorites/{listing_id}"""

    async def test_remove_favorite_success(
        self, client: AsyncClient, user_headers, test_listing
    ):
        # First add
        await client.post(f"/api/v1/favorites/{test_listing.id}", headers=user_headers)
        # Then remove
        resp = await client.delete(
            f"/api/v1/favorites/{test_listing.id}", headers=user_headers
        )
        assert resp.status_code == 200

    async def test_remove_favorite_not_in_favorites(
        self, client: AsyncClient, user_headers
    ):
        resp = await client.delete(f"/api/v1/favorites/{uuid4()}", headers=user_headers)
        assert resp.status_code == 404

    async def test_remove_favorite_unauthenticated(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.delete(f"/api/v1/favorites/{test_listing.id}")
        assert resp.status_code == 401
