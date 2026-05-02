"""HTTP-layer T-018 filter correctness tests.

Covers `GET /api/v1/listings` with Sprint 2 filter params:
    - matrix-gated drop (rent filter on sell request)
    - AND-match semantics for amenities
    - sale-finance boolean filters only include mortgage_ok=true matches
    - rent_period enum + min_rent_months list filter
    - ignore vs. 400 for cross-type filters (silent-drop)
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Currency,
    Listing,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
    SourceType,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _base_listing_kwargs(**over):
    """Common column set for a minimally valid ACTIVE / APPROVED listing."""
    defaults = dict(
        id=uuid4(),
        title="t",
        description="d",
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        price=50000,
        currency=Currency.USD,
        rooms=2,
        area=55.0,
        floor=3,
        total_floors=9,
        building_type="new",
        condition="euro",
        is_furnished=True,
        region="toshkent_shahri",
        district="mirzo_ulugbek",
        latitude=41.3,
        longitude=69.3,
        phone="+998901234567",
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
    )
    defaults.update(over)
    return defaults


class TestListFiltersSilentDrop:
    async def test_mortgage_filter_ignored_on_rent_request(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        """type=rent + mortgage_ok=true → mortgage_ok is silently dropped,
        rental listing still matches."""
        sale_with_mortgage = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                type=ListingType.SELL,
                mortgage_ok=True,
            )
        )
        rental = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                type=ListingType.RENT,
                price=600,
                rent_period="long_term",
                min_rent_months=6,
            )
        )
        db_session.add_all([sale_with_mortgage, rental])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/listings",
            params={"type": "rent", "mortgage_ok": "true"},
        )
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(rental.id) in ids
        # Sale listing must NOT leak in just because mortgage_ok=true matches.
        assert str(sale_with_mortgage.id) not in ids

    async def test_rent_period_ignored_on_sell_request(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        sale = Listing(**_base_listing_kwargs(seller_id=test_seller.id))
        rental = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                type=ListingType.RENT,
                price=500,
                rent_period="daily",
            )
        )
        db_session.add_all([sale, rental])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/listings",
            params={"type": "sell", "rent_period": "daily"},
        )
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(sale.id) in ids
        assert str(rental.id) not in ids


class TestSaleFinanceFilter:
    async def test_mortgage_ok_true_matches_only_flagged_listings(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        with_mortgage = Listing(
            **_base_listing_kwargs(seller_id=test_seller.id, mortgage_ok=True)
        )
        without_mortgage = Listing(
            **_base_listing_kwargs(seller_id=test_seller.id, mortgage_ok=False)
        )
        db_session.add_all([with_mortgage, without_mortgage])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/listings",
            params={"type": "sell", "mortgage_ok": "true"},
        )
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(with_mortgage.id) in ids
        assert str(without_mortgage.id) not in ids

    async def test_halol_ok_combined_with_deed_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        match = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                halol_ok=True,
                deed_type="cadastre",
            )
        )
        partial = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                halol_ok=True,
                deed_type="order",
            )
        )
        db_session.add_all([match, partial])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/listings",
            params={"halol_ok": "true", "deed_type": "cadastre"},
        )
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(match.id) in ids
        assert str(partial.id) not in ids


class TestRentFilters:
    async def test_rent_period_exact_match(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        long_term = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                type=ListingType.RENT,
                price=500,
                rent_period="long_term",
                min_rent_months=6,
            )
        )
        daily = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                type=ListingType.RENT,
                price=50,
                rent_period="daily",
            )
        )
        db_session.add_all([long_term, daily])
        await db_session.commit()

        resp = await client.get("/api/v1/listings", params={"rent_period": "daily"})
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(daily.id) in ids
        assert str(long_term.id) not in ids

    async def test_min_rent_months_list_filter(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        one_month = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                type=ListingType.RENT,
                price=400,
                rent_period="long_term",
                min_rent_months=1,
            )
        )
        twelve_month = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id,
                type=ListingType.RENT,
                price=400,
                rent_period="long_term",
                min_rent_months=12,
            )
        )
        db_session.add_all([one_month, twelve_month])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/listings",
            params=[("min_rent_months", 1), ("min_rent_months", 3)],
        )
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(one_month.id) in ids
        assert str(twelve_month.id) not in ids


class TestAmenityAndMatch:
    async def test_amenities_require_all_selected(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        has_both = Listing(
            **_base_listing_kwargs(
                seller_id=test_seller.id, amenities=["tv", "ac", "internet"]
            )
        )
        has_one = Listing(
            **_base_listing_kwargs(seller_id=test_seller.id, amenities=["tv"])
        )
        db_session.add_all([has_both, has_one])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/listings",
            params=[("amenities", "tv"), ("amenities", "ac")],
        )
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(has_both.id) in ids
        assert str(has_one.id) not in ids


class TestPR3Regression:
    async def test_existing_price_range_filter_unchanged(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        cheap = Listing(**_base_listing_kwargs(seller_id=test_seller.id, price=20000))
        pricey = Listing(**_base_listing_kwargs(seller_id=test_seller.id, price=200000))
        db_session.add_all([cheap, pricey])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/listings", params={"price_min": 50000, "price_max": 150000}
        )
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(cheap.id) not in ids
        assert str(pricey.id) not in ids

    async def test_empty_filters_returns_all_active_approved(
        self, client: AsyncClient, db_session: AsyncSession, test_seller
    ):
        listing = Listing(**_base_listing_kwargs(seller_id=test_seller.id))
        db_session.add(listing)
        await db_session.commit()

        resp = await client.get("/api/v1/listings")
        assert resp.status_code == 200
        ids = {item["id"] for item in resp.json()["items"]}
        assert str(listing.id) in ids

    async def test_malformed_filter_returns_422(self, client: AsyncClient):
        """rent_period outside the enum returns 422 from FastAPI."""
        resp = await client.get("/api/v1/listings", params={"rent_period": "weekly"})
        assert resp.status_code == 422
