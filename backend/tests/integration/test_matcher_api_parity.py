"""Matcher ⇔ API behavioral-parity safety net (PR7.1).

For every filter scenario, the saved-search matcher and the listings API
MUST agree on membership:

    listing_id ∈ GET /listings?<filters> results
        ⇔  _match_listing_to_filters(listing, ListingFilters(**<filters>))

These tests seed listings directly, hit both entry points, and compare the
resulting sets. Any future divergence between the SQL path and the
in-memory matcher will fail here before it ships.

No application-logic changes are introduced by this file.
"""

from __future__ import annotations

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
from app.schemas.listing import ListingFilters
from app.services.saved_search_matcher import _match_listing_to_filters

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _mk(**over) -> Listing:
    defaults = dict(
        id=uuid4(),
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        price=80000,
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
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
    )
    defaults.update(over)
    return Listing(**defaults)


async def _api_ids(client: AsyncClient, params) -> set[str]:
    """Fetch GET /listings with the given params. Accepts dict OR list of
    (key, value) tuples (for repeated keys). Returns the result id set.
    Pages up to 100 per call — tests below stay under that cap."""
    resp = await client.get("/api/v1/listings", params=params)
    assert resp.status_code == 200, resp.text
    return {item["id"] for item in resp.json()["items"]}


def _matcher_ids(listings: list[Listing], filters: ListingFilters) -> set[str]:
    return {
        str(listing.id)
        for listing in listings
        if _match_listing_to_filters(listing, filters)
    }


async def _assert_parity(
    client: AsyncClient,
    listings: list[Listing],
    http_params,
    filters: ListingFilters,
) -> set[str]:
    """Run both paths and assert byte-equal membership. Returns the
    matcher's id set so individual tests can add stronger assertions."""
    api_set = await _api_ids(client, http_params)
    mx_set = _matcher_ids(listings, filters)
    assert api_set == mx_set, (
        "API and matcher disagree:\n"
        f"  params = {http_params!r}\n"
        f"  only in API:     {sorted(api_set - mx_set)}\n"
        f"  only in matcher: {sorted(mx_set - api_set)}"
    )
    return mx_set


# ─────────────────────────────────────────────────────────────────────
# 1. Price range parity
# ─────────────────────────────────────────────────────────────────────


class TestPriceRangeParity:
    async def test_price_min_and_max(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        cheap = _mk(seller_id=test_seller.id, price=20_000)
        mid = _mk(seller_id=test_seller.id, price=80_000)
        pricey = _mk(seller_id=test_seller.id, price=200_000)
        db_session.add_all([cheap, mid, pricey])
        await db_session.commit()

        params = {"price_min": 50_000, "price_max": 100_000}
        matched = await _assert_parity(
            client,
            [cheap, mid, pricey],
            params,
            ListingFilters(price_min=50_000, price_max=100_000),
        )
        assert matched == {str(mid.id)}


# ─────────────────────────────────────────────────────────────────────
# 2. rent_period parity
# ─────────────────────────────────────────────────────────────────────


class TestRentPeriodParity:
    async def test_rent_period_daily(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        daily = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=80,
            rent_period="daily",
        )
        long_term = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=600,
            rent_period="long_term",
            min_rent_months=6,
        )
        sale = _mk(seller_id=test_seller.id)
        db_session.add_all([daily, long_term, sale])
        await db_session.commit()

        params = {"rent_period": "daily"}
        matched = await _assert_parity(
            client,
            [daily, long_term, sale],
            params,
            ListingFilters(rent_period="daily"),
        )
        # Silent-drop: rent_period is NOT applicable to sales, so the sale
        # listing is a trivial pass in both matcher and API.
        assert matched == {str(daily.id), str(sale.id)}


# ─────────────────────────────────────────────────────────────────────
# 3. mortgage_ok parity
# ─────────────────────────────────────────────────────────────────────


class TestMortgageParity:
    async def test_mortgage_ok_true(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        with_mortgage = _mk(seller_id=test_seller.id, mortgage_ok=True)
        without = _mk(seller_id=test_seller.id, mortgage_ok=False)
        rental = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            min_rent_months=6,
        )
        db_session.add_all([with_mortgage, without, rental])
        await db_session.commit()

        params = {"mortgage_ok": "true"}
        matched = await _assert_parity(
            client,
            [with_mortgage, without, rental],
            params,
            ListingFilters(mortgage_ok=True),
        )
        # Silent-drop: mortgage_ok isn't applicable to rentals. So the
        # rental is a trivial pass in both paths.
        assert matched == {str(with_mortgage.id), str(rental.id)}


# ─────────────────────────────────────────────────────────────────────
# 4. Amenities — AND match parity
# ─────────────────────────────────────────────────────────────────────


class TestAmenitiesParity:
    async def test_and_match(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        both = _mk(seller_id=test_seller.id, amenities=["tv", "ac", "internet"])
        one = _mk(seller_id=test_seller.id, amenities=["tv"])
        none = _mk(seller_id=test_seller.id, amenities=None)
        db_session.add_all([both, one, none])
        await db_session.commit()

        http_params = [("amenities", "tv"), ("amenities", "ac")]
        matched = await _assert_parity(
            client,
            [both, one, none],
            http_params,
            ListingFilters(amenities=["tv", "ac"]),
        )
        assert matched == {str(both.id)}


# ─────────────────────────────────────────────────────────────────────
# 5. rent_payment — OR (overlap) parity
# ─────────────────────────────────────────────────────────────────────


class TestRentPaymentParity:
    async def test_or_match(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        payme_user = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            min_rent_months=6,
            rent_payment=["payme"],
        )
        cash_user = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            min_rent_months=6,
            rent_payment=["cash"],
        )
        no_payment = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            min_rent_months=6,
            rent_payment=None,
        )
        db_session.add_all([payme_user, cash_user, no_payment])
        await db_session.commit()

        http_params = [
            ("type", "rent"),
            ("rent_payment", "payme"),
            ("rent_payment", "click"),
        ]
        matched = await _assert_parity(
            client,
            [payme_user, cash_user, no_payment],
            http_params,
            ListingFilters(type="rent", rent_payment=["payme", "click"]),
        )
        assert matched == {str(payme_user.id)}


# ─────────────────────────────────────────────────────────────────────
# 6. Applicability drop — rent filter on sell request
# ─────────────────────────────────────────────────────────────────────


class TestApplicabilityDropParity:
    async def test_rent_filter_dropped_on_sell(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        sale = _mk(seller_id=test_seller.id)
        rental = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=600,
            rent_period="daily",
        )
        db_session.add_all([sale, rental])
        await db_session.commit()

        params = {"type": "sell", "rent_period": "daily"}
        matched = await _assert_parity(
            client,
            [sale, rental],
            params,
            ListingFilters(type="sell", rent_period="daily"),
        )
        # type=sell filters out the rental; rent_period is silently
        # dropped. Only the sale remains in both paths.
        assert matched == {str(sale.id)}


# ─────────────────────────────────────────────────────────────────────
# 7. Partial filter — only `type` set
# ─────────────────────────────────────────────────────────────────────


class TestPartialFilterParity:
    async def test_only_type(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        sale = _mk(seller_id=test_seller.id)
        rental = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            min_rent_months=6,
        )
        db_session.add_all([sale, rental])
        await db_session.commit()

        params = {"type": "rent"}
        matched = await _assert_parity(
            client,
            [sale, rental],
            params,
            ListingFilters(type="rent"),
        )
        assert matched == {str(rental.id)}


# ─────────────────────────────────────────────────────────────────────
# 8. Mixed complex filter — property_type + type + mortgage + price range
# ─────────────────────────────────────────────────────────────────────


class TestMixedFilterParity:
    async def test_complex_intersection(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
    ):
        target = _mk(
            seller_id=test_seller.id,
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            price=120_000,
            mortgage_ok=True,
        )
        too_cheap = _mk(
            seller_id=test_seller.id,
            price=30_000,
            mortgage_ok=True,
        )
        no_mortgage = _mk(
            seller_id=test_seller.id,
            price=120_000,
            mortgage_ok=False,
        )
        house_with_mortgage = _mk(
            seller_id=test_seller.id,
            property_type=PropertyType.HOUSE,
            price=120_000,
            mortgage_ok=True,
            # House doesn't have floor in the matrix — null is fine.
            floor=None,
            building_type=None,
        )
        rental = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            min_rent_months=6,
        )
        db_session.add_all(
            [target, too_cheap, no_mortgage, house_with_mortgage, rental]
        )
        await db_session.commit()

        params = {
            "type": "sell",
            "property_type": "apartment",
            "mortgage_ok": "true",
            "price_min": 70_000,
        }
        matched = await _assert_parity(
            client,
            [target, too_cheap, no_mortgage, house_with_mortgage, rental],
            params,
            ListingFilters(
                type="sell",
                property_type="apartment",
                mortgage_ok=True,
                price_min=70_000,
            ),
        )
        assert matched == {str(target.id)}
