"""Tests for preferences API endpoints."""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestGetPreferences:
    """GET /api/v1/preferences"""

    async def test_get_preferences_default(self, client: AsyncClient, user_headers):
        resp = await client.get("/api/v1/preferences", headers=user_headers)
        assert resp.status_code == 200

    async def test_get_preferences_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/preferences")
        assert resp.status_code == 401


class TestUpdatePreferences:
    """PUT /api/v1/preferences"""

    async def test_update_preferences(self, client: AsyncClient, user_headers):
        resp = await client.put(
            "/api/v1/preferences",
            json={
                "regions": ["tashkent"],
                "property_types": ["apartment"],
                "listing_types": ["sell"],
                "price_min": 10000,
                "price_max": 100000,
                "rooms": [2, 3],
            },
            headers=user_headers,
        )
        assert resp.status_code == 200

    async def test_update_preferences_unauthenticated(self, client: AsyncClient):
        resp = await client.put("/api/v1/preferences", json={"regions": ["tashkent"]})
        assert resp.status_code == 401
