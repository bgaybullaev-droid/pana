"""Tests for notifications API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestGetNotificationPreferences:
    """GET /api/v1/notifications/preferences"""

    async def test_get_preferences_default(self, client: AsyncClient, user_headers):
        resp = await client.get(
            "/api/v1/notifications/preferences", headers=user_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data

    async def test_get_preferences_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/notifications/preferences")
        assert resp.status_code == 401


class TestUpdateNotificationPreferences:
    """PUT /api/v1/notifications/preferences"""

    async def test_update_preferences(self, client: AsyncClient, user_headers):
        resp = await client.put(
            "/api/v1/notifications/preferences",
            json={"enabled": True, "daily_limit": 10},
            headers=user_headers,
        )
        assert resp.status_code == 200

    async def test_update_preferences_unauthenticated(self, client: AsyncClient):
        resp = await client.put(
            "/api/v1/notifications/preferences", json={"enabled": True}
        )
        assert resp.status_code == 401


class TestGetNotifications:
    """GET /api/v1/notifications"""

    async def test_get_notifications_empty(self, client: AsyncClient, user_headers):
        resp = await client.get("/api/v1/notifications", headers=user_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_get_notifications_unread_only(
        self, client: AsyncClient, user_headers
    ):
        resp = await client.get(
            "/api/v1/notifications", params={"unread_only": True}, headers=user_headers
        )
        assert resp.status_code == 200

    async def test_get_notifications_pagination(
        self, client: AsyncClient, user_headers
    ):
        resp = await client.get(
            "/api/v1/notifications",
            params={"page": 1, "per_page": 5},
            headers=user_headers,
        )
        assert resp.status_code == 200


class TestUnreadCount:
    """GET /api/v1/notifications/unread-count"""

    async def test_get_unread_count(self, client: AsyncClient, user_headers):
        resp = await client.get(
            "/api/v1/notifications/unread-count", headers=user_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "unread_count" in data
        assert data["unread_count"] >= 0


class TestMarkRead:
    """POST /api/v1/notifications/mark-read"""

    async def test_mark_all_read(self, client: AsyncClient, user_headers):
        resp = await client.post(
            "/api/v1/notifications/mark-read", json={}, headers=user_headers
        )
        assert resp.status_code == 200


class TestDeleteNotification:
    """DELETE /api/v1/notifications/{notification_id}"""

    async def test_delete_notification_not_found(
        self, client: AsyncClient, user_headers
    ):
        resp = await client.delete(
            f"/api/v1/notifications/{uuid4()}", headers=user_headers
        )
        assert resp.status_code == 404
