"""Tests for comments API endpoints."""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Comment

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestGetComments:
    """GET /api/v1/listings/{listing_id}/comments"""

    async def test_get_comments_empty(self, client: AsyncClient, test_listing):
        resp = await client.get(f"/api/v1/listings/{test_listing.id}/comments")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert data["total"] == 0

    async def test_get_comments_not_found_listing(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/listings/{uuid4()}/comments")
        assert resp.status_code in [200, 404]


class TestCreateComment:
    """POST /api/v1/listings/{listing_id}/comments"""

    async def test_create_comment_success(
        self, client: AsyncClient, user_headers, test_listing
    ):
        resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": "Great listing!"},
            headers=user_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["text"] == "Great listing!"

    async def test_create_comment_unauthenticated(
        self, client: AsyncClient, test_listing
    ):
        resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": "Test"},
        )
        assert resp.status_code == 401

    async def test_create_comment_empty_text(
        self, client: AsyncClient, user_headers, test_listing
    ):
        resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": ""},
            headers=user_headers,
        )
        assert resp.status_code == 422

    async def test_create_reply(self, client: AsyncClient, user_headers, test_listing):
        # Create parent comment
        parent_resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": "Parent comment"},
            headers=user_headers,
        )
        parent_id = parent_resp.json()["id"]
        # Create reply
        resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": "Reply comment", "parent_id": parent_id},
            headers=user_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["parent_id"] == parent_id


class TestDeleteComment:
    """DELETE /api/v1/listings/{listing_id}/comments/{comment_id}"""

    async def test_delete_own_comment(
        self, client: AsyncClient, user_headers, test_listing
    ):
        # Create comment
        create_resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": "To delete"},
            headers=user_headers,
        )
        comment_id = create_resp.json()["id"]
        # Delete
        resp = await client.delete(
            f"/api/v1/listings/{test_listing.id}/comments/{comment_id}",
            headers=user_headers,
        )
        assert resp.status_code == 200

    async def test_delete_comment_not_owner(
        self, client: AsyncClient, seller_headers, user_headers, test_listing
    ):
        # Create as user
        create_resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": "Test"},
            headers=user_headers,
        )
        comment_id = create_resp.json()["id"]
        # Try delete as seller
        resp = await client.delete(
            f"/api/v1/listings/{test_listing.id}/comments/{comment_id}",
            headers=seller_headers,
        )
        assert resp.status_code in [403, 404]


class TestLikeComment:
    """POST /api/v1/listings/{listing_id}/comments/{comment_id}/like"""

    async def test_like_comment_success(
        self, client: AsyncClient, user_headers, test_listing
    ):
        # Create comment
        create_resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": "Likeable"},
            headers=user_headers,
        )
        comment_id = create_resp.json()["id"]
        # Like
        resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments/{comment_id}/like",
            headers=user_headers,
        )
        assert resp.status_code == 201

    async def test_unlike_comment(
        self, client: AsyncClient, user_headers, test_listing
    ):
        # Create and like
        create_resp = await client.post(
            f"/api/v1/listings/{test_listing.id}/comments",
            json={"text": "Unlikeable"},
            headers=user_headers,
        )
        comment_id = create_resp.json()["id"]
        await client.post(
            f"/api/v1/listings/{test_listing.id}/comments/{comment_id}/like",
            headers=user_headers,
        )
        # Unlike
        resp = await client.delete(
            f"/api/v1/listings/{test_listing.id}/comments/{comment_id}/like",
            headers=user_headers,
        )
        assert resp.status_code == 200
