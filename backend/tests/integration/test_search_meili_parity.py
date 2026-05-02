"""PR10 — Postgres ⇔ Meilisearch result parity safety net.

For every filter scenario, the router's Postgres path and Meili path
MUST return the same set of listing IDs:

    set(pg_ids) == set(meili_ids)

These tests seed listings into both Postgres and Meili (via
`index_listing` used by PR8), flip `settings.search_backend` between
runs, and compare the API's returned ID set on each side.

All tests gracefully skip when Meilisearch is unavailable — they are
CI-gated on an environment that has both Postgres and Meili running.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import (
    Currency,
    Listing,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
    SourceType,
)
from app.services.search_index import ensure_index_exists, index_listing

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


# ─────────────────────────────────────────────────────────────────────
# Auto-skip when Meili is unreachable
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _require_meili():
    """Skip every test in this file if Meilisearch isn't available.

    The tests only exist to PROVE parity when both engines run — running
    them without Meili is meaningless (and every test would trivially
    pass because the router would fall back to Postgres on both sides).
    """
    if ensure_index_exists() is None:
        pytest.skip("Meilisearch unavailable; parity tests require live Meili")


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
    resp = await client.get("/api/v1/listings", params=params)
    assert resp.status_code == 200, resp.text
    return {item["id"] for item in resp.json()["items"]}


async def _assert_parity(
    client: AsyncClient,
    db_session: AsyncSession,
    listings: list[Listing],
    params,
) -> set[str]:
    """Seed the listings in both backends, hit the API once with
    flag=postgres and once with flag=meili, assert ID-set equality."""
    db_session.add_all(listings)
    await db_session.commit()
    for listing in listings:
        # PR8 write hooks already index new rows, but we index explicitly
        # here to make the test self-contained (the test may run in a
        # transaction that never commits to Meili in the real flow).
        index_listing(listing)

    # Let Meili finish indexing (async under the hood).
    import asyncio as _asyncio

    await _asyncio.sleep(0.3)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "search_backend", "postgres")
        pg_ids = await _api_ids(client, params)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(settings, "search_backend", "meili")
        meili_ids = await _api_ids(client, params)

    assert pg_ids == meili_ids, (
        f"parity mismatch for params={params!r}:\n"
        f"  only PG:    {sorted(pg_ids - meili_ids)}\n"
        f"  only Meili: {sorted(meili_ids - pg_ids)}"
    )
    return pg_ids


# ─────────────────────────────────────────────────────────────────────
# Parity cases
# ─────────────────────────────────────────────────────────────────────


class TestParity:
    async def test_price_range(
        self, client: AsyncClient, db_session: AsyncSession, test_seller
    ):
        rows = [
            _mk(seller_id=test_seller.id, price=20_000),
            _mk(seller_id=test_seller.id, price=80_000),
            _mk(seller_id=test_seller.id, price=200_000),
        ]
        matched = await _assert_parity(
            client,
            db_session,
            rows,
            {"price_min": 50_000, "price_max": 100_000},
        )
        assert matched == {str(rows[1].id)}

    async def test_type_filter(
        self, client: AsyncClient, db_session: AsyncSession, test_seller
    ):
        sale = _mk(seller_id=test_seller.id)
        rental = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
        )
        matched = await _assert_parity(
            client, db_session, [sale, rental], {"type": "rent"}
        )
        assert matched == {str(rental.id)}

    async def test_rent_sell_separation_silent_drop(
        self, client: AsyncClient, db_session: AsyncSession, test_seller
    ):
        """mortgage_ok on a type=rent request must silently drop.
        Both backends must return only the rental listing (sale is
        excluded by the type predicate)."""
        sale = _mk(seller_id=test_seller.id, mortgage_ok=True)
        rental = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
        )
        matched = await _assert_parity(
            client,
            db_session,
            [sale, rental],
            {"type": "rent", "mortgage_ok": "true"},
        )
        assert matched == {str(rental.id)}

    async def test_amenities_AND_match(
        self, client: AsyncClient, db_session: AsyncSession, test_seller
    ):
        both = _mk(seller_id=test_seller.id, amenities=["tv", "ac", "internet"])
        one = _mk(seller_id=test_seller.id, amenities=["tv"])
        none = _mk(seller_id=test_seller.id, amenities=None)
        matched = await _assert_parity(
            client,
            db_session,
            [both, one, none],
            [("amenities", "tv"), ("amenities", "ac")],
        )
        assert matched == {str(both.id)}

    async def test_rent_payment_OR_match(
        self, client: AsyncClient, db_session: AsyncSession, test_seller
    ):
        payme = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            rent_payment=["payme"],
        )
        cash = _mk(
            seller_id=test_seller.id,
            type=ListingType.RENT,
            price=500,
            rent_period="long_term",
            rent_payment=["cash"],
        )
        matched = await _assert_parity(
            client,
            db_session,
            [payme, cash],
            [
                ("type", "rent"),
                ("rent_payment", "payme"),
                ("rent_payment", "click"),
            ],
        )
        assert matched == {str(payme.id)}

    async def test_mortgage_ok_true(
        self, client: AsyncClient, db_session: AsyncSession, test_seller
    ):
        with_m = _mk(seller_id=test_seller.id, mortgage_ok=True)
        without = _mk(seller_id=test_seller.id, mortgage_ok=False)
        matched = await _assert_parity(
            client,
            db_session,
            [with_m, without],
            {"type": "sell", "mortgage_ok": "true"},
        )
        assert matched == {str(with_m.id)}

    async def test_mixed_complex_filter(
        self, client: AsyncClient, db_session: AsyncSession, test_seller
    ):
        target = _mk(
            seller_id=test_seller.id,
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            price=120_000,
            mortgage_ok=True,
        )
        too_cheap = _mk(seller_id=test_seller.id, price=30_000, mortgage_ok=True)
        no_mort = _mk(seller_id=test_seller.id, price=120_000, mortgage_ok=False)
        house = _mk(
            seller_id=test_seller.id,
            property_type=PropertyType.HOUSE,
            price=120_000,
            mortgage_ok=True,
            floor=None,
            building_type=None,
        )
        matched = await _assert_parity(
            client,
            db_session,
            [target, too_cheap, no_mort, house],
            {
                "type": "sell",
                "property_type": "apartment",
                "mortgage_ok": "true",
                "price_min": 70_000,
            },
        )
        assert matched == {str(target.id)}
