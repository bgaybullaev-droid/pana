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

    async def test_feed_with_multivalue_type(self, client: AsyncClient, test_listing):
        # The buyer filter drawer offers multi-select chips; both values must
        # be honoured (repeated query params), not just the first one.
        resp = await client.get(
            "/api/v1/listings/feed",
            params=[("type", "sell"), ("type", "rent"), ("page", 1)],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

    async def test_feed_rejects_invalid_type(self, client: AsyncClient):
        resp = await client.get("/api/v1/listings/feed", params={"type": "bogus"})
        assert resp.status_code == 422

    async def test_feed_sort_newest(self, client: AsyncClient, test_listing):
        resp = await client.get("/api/v1/listings/feed", params={"sort": "newest"})
        assert resp.status_code == 200

    async def test_feed_sort_price_asc(self, client: AsyncClient, test_listing):
        resp = await client.get("/api/v1/listings/feed", params={"sort": "price_asc"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        prices = [i["price"] for i in items if i["price"] is not None]
        assert prices == sorted(prices)

    async def test_feed_sort_price_desc(self, client: AsyncClient, test_listing):
        resp = await client.get("/api/v1/listings/feed", params={"sort": "price_desc"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        prices = [i["price"] for i in items if i["price"] is not None]
        assert prices == sorted(prices, reverse=True)

    async def test_feed_rejects_invalid_sort(self, client: AsyncClient):
        resp = await client.get("/api/v1/listings/feed", params={"sort": "bogus"})
        assert resp.status_code == 422

    # ── Wave-1 attribute filters ────────────────────────────────────────
    async def test_feed_area_range(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"area_min": 30, "area_max": 200}
        )
        assert resp.status_code == 200
        assert "items" in resp.json()

    async def test_feed_floor_range(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"floor_min": 2, "floor_max": 9}
        )
        assert resp.status_code == 200

    async def test_feed_total_floors_range(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed",
            params={"total_floors_min": 5, "total_floors_max": 16},
        )
        assert resp.status_code == 200

    async def test_feed_not_first_floor(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"not_first_floor": "true"}
        )
        assert resp.status_code == 200
        # Every returned row must be on a known floor other than 1.
        for item in resp.json()["items"]:
            if item.get("floor") is not None:
                assert item["floor"] != 1

    async def test_feed_not_last_floor(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"not_last_floor": "true"}
        )
        assert resp.status_code == 200

    async def test_feed_building_type(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"building_type": "new"}
        )
        assert resp.status_code == 200

    async def test_feed_rejects_invalid_building_type(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/listings/feed", params={"building_type": "bogus"}
        )
        assert resp.status_code == 422

    async def test_feed_condition_multi(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed",
            params=[("condition", "euro"), ("condition", "cosmetic")],
        )
        assert resp.status_code == 200

    async def test_feed_has_photo(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"has_photo": "true"}
        )
        assert resp.status_code == 200

    async def test_feed_has_photo_tolerates_non_array_images(
        self, client: AsyncClient, db_session, test_listing
    ):
        # Regression: crawler rows store mixed image shapes (legacy rows
        # hold a JSON object, not an array). Postgres does not guarantee
        # AND evaluation order, so a naive jsonb_array_length() predicate
        # aborted the whole feed query with «cannot get array length of a
        # non-array» → 500. The CASE-guarded predicate must skip such rows.
        from app.db.models import TelegramListing

        bad_row = TelegramListing(
            property_type="apartment",
            listing_type="sell",
            price=51234,
            currency="USD",
            images={"cover": "legacy-object-shape.jpg"},
        )
        db_session.add(bad_row)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/listings/feed", params={"has_photo": "true"}
        )
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(bad_row.id) not in ids

    async def test_feed_posted_within(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"posted_within": 7}
        )
        assert resp.status_code == 200

    # ── Deal-terms filters (platform-only) ──────────────────────────────
    async def test_feed_mortgage_ok(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"mortgage_ok": "true"}
        )
        assert resp.status_code == 200

    async def test_feed_furnished(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"furnished": "true"}
        )
        assert resp.status_code == 200

    async def test_feed_rent_period(self, client: AsyncClient, test_listing):
        resp = await client.get(
            "/api/v1/listings/feed", params={"rent_period": "long_term"}
        )
        assert resp.status_code == 200

    async def test_feed_rejects_invalid_rent_period(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/listings/feed", params={"rent_period": "weekly"}
        )
        assert resp.status_code == 422

    async def test_feed_deal_terms_exclude_crawler(
        self, client: AsyncClient, test_listing
    ):
        # An active deal-terms filter must restrict the feed to platform
        # listings — crawler sources can't satisfy these columns.
        resp = await client.get(
            "/api/v1/listings/feed", params={"halol_ok": "true"}
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["source"] == "main"


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
