"""Tests for crawler import API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestTelegramImport:
    """POST /api/v1/crawler/telegram/import"""

    async def test_import_telegram_listings(self, client: AsyncClient):
        payload = {
            "listings": [
                {
                    "source_channel": "test_channel",
                    "message_id": 12345,
                    "title": "Test Telegram Listing",
                    "description": "A listing from Telegram",
                    "price": 30000,
                    "currency": "usd",
                    "property_type": "apartment",
                    "listing_type": "sell",
                    "rooms": 2,
                    "area": 50.0,
                    "region": "tashkent",
                    "phone": "+998901111111",
                    "images": ["https://example.com/img1.jpg"],
                }
            ]
        }
        resp = await client.post("/api/v1/crawler/telegram/import", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert "imported" in data or "created" in data or "total" in data


class TestTelegramListings:
    """GET /api/v1/crawler/telegram/listings"""

    async def test_list_telegram_listings(self, client: AsyncClient):
        resp = await client.get("/api/v1/crawler/telegram/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_list_telegram_with_filters(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/crawler/telegram/listings", params={"property_type": "apartment"}
        )
        assert resp.status_code == 200


class TestOLXImport:
    """POST /api/v1/crawler/olx/import"""

    async def test_import_olx_listings(self, client: AsyncClient):
        payload = {
            "listings": [
                {
                    "olx_id": "olx_test_123",
                    "url": "https://olx.uz/ad/test-123",
                    "title": "Test OLX Listing",
                    "description": "A listing from OLX",
                    "price": 40000,
                    "currency": "usd",
                    "property_type": "house",
                    "listing_type": "sell",
                    "region": "tashkent",
                    "phone": "+998902222222",
                    "images": ["https://example.com/img2.jpg"],
                }
            ]
        }
        resp = await client.post("/api/v1/crawler/olx/import", json=payload)
        assert resp.status_code == 201


class TestOLXListings:
    """GET /api/v1/crawler/olx/listings"""

    async def test_list_olx_listings(self, client: AsyncClient):
        resp = await client.get("/api/v1/crawler/olx/listings")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
