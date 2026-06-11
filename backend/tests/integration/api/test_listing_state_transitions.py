"""State transition / visibility matrix enforcement tests (T-024, Sprint 1).

Covers _clear_incompatible_fields: POST and PATCH /listings must wipe fields
that are not visible for the listing's (property_type, deal_type) combo,
and be a no-op for unchanged listings. (Rule P3 — land forces sell — was
retired when land × rent became a legal combo.)
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


def _valid_apartment_payload(**overrides):
    """Minimal valid POST payload for an apartment listing."""
    payload = {
        "title": "Transition Test Apt",
        "description": "Testing visibility matrix",
        "type": "sell",
        "property_type": "apartment",
        "price": 60000,
        "currency": "USD",
        "rooms": 2,
        "area": 55.0,
        "floor": 3,
        "total_floors": 9,
        "building_type": "new",
        "condition": "euro",
        "is_furnished": True,
        "region": "toshkent_shahri",
        "district": "mirzo_ulugbek",
        "latitude": 41.3,
        "longitude": 69.3,
        "phone": "+998901234567",
        "images": [{"original_url": "http://example.com/img.jpg", "position": 0}],
    }
    payload.update(overrides)
    return payload


def _valid_house_payload(**overrides):
    payload = {
        "title": "Transition Test House",
        "description": "Testing visibility matrix",
        "type": "sell",
        "property_type": "house",
        "price": 120000,
        "currency": "USD",
        "rooms": 4,
        "area": 180.0,
        "total_floors": 2,
        "land_area": 8.0,
        "house_type": "cottage",
        "is_furnished": False,
        "region": "toshkent_shahri",
        "district": "mirzo_ulugbek",
        "latitude": 41.3,
        "longitude": 69.3,
        "phone": "+998901234567",
        "images": [{"original_url": "http://example.com/img.jpg", "position": 0}],
    }
    payload.update(overrides)
    return payload


class TestCreateClearing:
    """POST /api/v1/listings — rule P1 (allowlist)."""

    async def test_apartment_create_wipes_house_only_field(
        self, client: AsyncClient, seller_headers
    ):
        """house_type is not in the apartment allowlist → must be cleared."""
        payload = _valid_apartment_payload(house_type="cottage")
        resp = await client.post(
            "/api/v1/listings", json=payload, headers=seller_headers
        )
        assert resp.status_code == 201
        assert resp.json()["house_type"] is None

    async def test_commercial_create_wipes_rooms_and_amenities(
        self, client: AsyncClient, seller_headers
    ):
        """rooms / amenities are apartment-or-house only."""
        payload = _valid_apartment_payload(
            property_type="commercial",
            rooms=3,
            amenities=["tv", "ac"],
        )
        resp = await client.post(
            "/api/v1/listings", json=payload, headers=seller_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["property_type"] == "commercial"
        assert body["rooms"] is None
        assert body["amenities"] in (None, [])

    async def test_land_rent_is_legal_and_keeps_rent_fields(
        self, client: AsyncClient, seller_headers
    ):
        """land × rent is a legal combo: type stays rent, rent group survives."""
        payload = {
            "type": "rent",
            "property_type": "land",
            "price": 25000,
            "currency": "USD",
            "land_area": 10.0,
            "land_purpose": "construction",
            "rent_period": "long_term",
            "min_rent_months": 6,
            "region": "toshkent_shahri",
            "district": "mirzo_ulugbek",
            "latitude": 41.3,
            "longitude": 69.3,
            "phone": "+998901234567",
            "images": [{"original_url": "http://example.com/img.jpg", "position": 0}],
        }
        resp = await client.post(
            "/api/v1/listings", json=payload, headers=seller_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["type"] == "rent"
        assert body["rent_period"] == "long_term"
        assert body["min_rent_months"] == 6

    async def test_land_create_wipes_apartment_fields(
        self, client: AsyncClient, seller_headers
    ):
        """Only land_area + land_purpose survive the matrix on land × sell."""
        payload = {
            "type": "sell",
            "property_type": "land",
            "price": 25000,
            "currency": "USD",
            "land_area": 10.0,
            "land_purpose": "private",
            "rooms": 3,
            "area": 100.0,
            "floor": 2,
            "total_floors": 5,
            "building_type": "new",
            "condition": "euro",
            "is_furnished": True,
            "amenities": ["tv"],
            "region": "toshkent_shahri",
            "district": "mirzo_ulugbek",
            "latitude": 41.3,
            "longitude": 69.3,
            "phone": "+998901234567",
            "images": [{"original_url": "http://example.com/img.jpg", "position": 0}],
        }
        resp = await client.post(
            "/api/v1/listings", json=payload, headers=seller_headers
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["land_area"] == 10.0
        assert body["land_purpose"] == "private"
        for wiped in (
            "rooms",
            "area",
            "floor",
            "total_floors",
            "building_type",
            "condition",
            "is_furnished",
        ):
            assert body[wiped] is None, f"{wiped} should be cleared on land listing"


class TestUpdateClearing:
    """PATCH /api/v1/listings/{id} — clearing on property_type / type change."""

    async def _make_apartment(
        self,
        db_session: AsyncSession,
        test_seller,
        **overrides,
    ) -> Listing:
        listing = Listing(
            id=uuid4(),
            seller_id=test_seller.id,
            title="PATCH source apt",
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            price=50000,
            currency=Currency.USD,
            rooms=2,
            area=60.0,
            floor=3,
            total_floors=9,
            building_type="new",
            condition="euro",
            kitchen_area=10.0,
            living_area=40.0,
            is_furnished=True,
            amenities=["tv", "ac"],
            region="toshkent_shahri",
            district="mirzo_ulugbek",
            latitude=41.3,
            longitude=69.3,
            phone="+998901234567",
            status=ListingStatus.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
            source_type=SourceType.MANUAL,
        )
        for k, v in overrides.items():
            setattr(listing, k, v)
        db_session.add(listing)
        await db_session.commit()
        await db_session.refresh(listing)
        return listing

    async def test_patch_apt_to_house_clears_apt_only_fields(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seller_headers,
        test_seller,
    ):
        """Switching an apartment to house wipes building_type / kitchen_area /
        condition / floor, while accepting the new house-only fields."""
        apt = await self._make_apartment(db_session, test_seller)
        patch = {
            "property_type": "house",
            "land_area": 6.0,
            "house_type": "cottage",
            "total_floors": 2,
        }
        resp = await client.patch(
            f"/api/v1/listings/{apt.id}", json=patch, headers=seller_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["property_type"] == "house"
        assert body["house_type"] == "cottage"
        assert body["land_area"] == 6.0
        for wiped in ("building_type", "kitchen_area", "condition", "floor"):
            assert body[wiped] is None, f"{wiped} should be cleared on → house"

    async def test_patch_apt_to_land_wipes_almost_everything_keeps_rent(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seller_headers,
        test_seller,
    ):
        apt = await self._make_apartment(
            db_session, test_seller, type=ListingType.RENT, rent_period="daily"
        )
        patch = {
            "property_type": "land",
            "land_area": 5.0,
            "land_purpose": "private",
        }
        resp = await client.patch(
            f"/api/v1/listings/{apt.id}", json=patch, headers=seller_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["property_type"] == "land"
        assert body["type"] == "rent"  # land × rent is legal — no coercion
        for wiped in (
            "rooms",
            "floor",
            "total_floors",
            "building_type",
            "condition",
            "kitchen_area",
            "living_area",
            "is_furnished",
            "amenities",
        ):
            assert body[wiped] in (None, []), f"{wiped} should be cleared on → land"

    async def test_noop_patch_preserves_all_fields(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seller_headers,
        test_seller,
    ):
        """Patch with only a price change leaves every matrix field untouched."""
        apt = await self._make_apartment(db_session, test_seller)
        resp = await client.patch(
            f"/api/v1/listings/{apt.id}",
            json={"price": 51000},
            headers=seller_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["price"] == 51000
        assert body["rooms"] == 2
        assert body["building_type"] == "new"
        assert body["kitchen_area"] == 10.0
        assert body["condition"] == "euro"
        assert body["amenities"] == ["tv", "ac"]

    async def test_patch_apt_to_commercial_clears_rooms_amenities_kitchen(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seller_headers,
        test_seller,
    ):
        apt = await self._make_apartment(db_session, test_seller)
        patch = {"property_type": "commercial"}
        resp = await client.patch(
            f"/api/v1/listings/{apt.id}", json=patch, headers=seller_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["property_type"] == "commercial"
        for wiped in (
            "rooms",
            "kitchen_area",
            "living_area",
            "building_type",
            "amenities",
        ):
            assert body[wiped] in (
                None,
                [],
            ), f"{wiped} should not be visible on commercial"
        # commercial keeps floor / area / condition / is_furnished
        assert body["floor"] == 3
        assert body["area"] == 60.0
        assert body["condition"] == "euro"


class TestClearHelperUnit:
    """Direct unit tests on _clear_incompatible_fields (no HTTP)."""

    async def test_helper_idempotent_on_consistent_state(
        self, db_session: AsyncSession
    ):
        """Running the helper twice on a clean listing changes nothing."""
        from app.api.v1.listings import _clear_incompatible_fields

        listing = Listing(
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            price=1,
            currency=Currency.USD,
            rooms=2,
            area=50.0,
            floor=1,
            total_floors=5,
            building_type="new",
            condition="euro",
        )
        first = _clear_incompatible_fields(listing)
        second = _clear_incompatible_fields(listing)
        assert first == []
        assert second == []

    async def test_helper_returns_list_of_cleared_fields(
        self, db_session: AsyncSession
    ):
        from app.api.v1.listings import _clear_incompatible_fields

        listing = Listing(
            type=ListingType.SELL,
            property_type=PropertyType.LAND,
            price=1,
            currency=Currency.USD,
            # Invisible-for-land fields populated on purpose:
            rooms=3,
            area=50.0,
            building_type="new",
            condition="euro",
            is_furnished=True,
        )
        cleared = _clear_incompatible_fields(listing)
        assert "rooms" in cleared
        assert "area" in cleared
        assert "building_type" in cleared
        assert "condition" in cleared
        assert "is_furnished" in cleared
        assert listing.rooms is None
        assert listing.building_type is None
        assert listing.is_furnished is None

    async def test_helper_keeps_land_rent_combo(self, db_session: AsyncSession):
        """P3 retired: land × rent passes through the helper unchanged."""
        from app.api.v1.listings import _clear_incompatible_fields

        listing = Listing(
            type=ListingType.RENT,
            property_type=PropertyType.LAND,
            price=1,
            currency=Currency.USD,
        )
        _clear_incompatible_fields(listing)
        assert listing.type == ListingType.RENT


# ─────────────────────────────────────────────────────────────────────
# Sprint 2 — Rule P2 (rent ↔ sell) + P4 (rent_period sub-gate) + required
# ─────────────────────────────────────────────────────────────────────


class TestRuleP2UnitHelper:
    """Direct unit tests for rule P2 (sale/rent group split)."""

    async def test_rent_listing_clears_sale_finance(self, db_session: AsyncSession):
        """A rental must not carry mortgage_ok / installment_ok / halol_ok / deed_type."""
        from app.api.v1.listings import _clear_incompatible_fields

        listing = Listing(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=1000,
            currency=Currency.USD,
            rooms=1,
            area=40.0,
            floor=2,
            total_floors=9,
            building_type="secondary",
            condition="euro",
            is_furnished=True,
            # Sale-only values that must be wiped on rent:
            mortgage_ok=True,
            installment_ok=True,
            halol_ok=True,
            deed_type="cadastre",
        )
        cleared = _clear_incompatible_fields(listing)
        assert "mortgage_ok" in cleared
        assert "installment_ok" in cleared
        assert "halol_ok" in cleared
        assert "deed_type" in cleared
        assert listing.mortgage_ok is False
        assert listing.installment_ok is False
        assert listing.halol_ok is False
        assert listing.deed_type is None

    async def test_sell_listing_clears_rent_group(self, db_session: AsyncSession):
        """A sale must not carry rent_period, deposit, utilities_incl, etc."""
        from app.api.v1.listings import _clear_incompatible_fields

        listing = Listing(
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            price=50000,
            currency=Currency.USD,
            rooms=2,
            area=60.0,
            floor=3,
            total_floors=9,
            building_type="new",
            condition="euro",
            is_furnished=False,
            # Rent-only values that must be wiped on sell:
            rent_period="long_term",
            deposit=500,
            utilities_incl=True,
            min_rent_months=6,
            allowed_students=True,
            allowed_pets=False,
            rent_payment=["cash", "payme"],
        )
        cleared = _clear_incompatible_fields(listing)
        for field in (
            "rent_period",
            "deposit",
            "utilities_incl",
            "min_rent_months",
            "allowed_students",
            "allowed_pets",
            "rent_payment",
        ):
            assert field in cleared, f"{field} should be cleared on sell"
        assert listing.rent_period is None
        assert listing.deposit is None
        assert listing.min_rent_months is None
        assert listing.rent_payment is None

    async def test_rule_p4_daily_rent_clears_min_rent_months(
        self, db_session: AsyncSession
    ):
        """min_rent_months is only valid for rent_period='long_term'."""
        from app.api.v1.listings import _clear_incompatible_fields

        listing = Listing(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=100,
            currency=Currency.USD,
            rooms=1,
            area=35.0,
            floor=1,
            total_floors=5,
            building_type="new",
            condition="euro",
            is_furnished=True,
            rent_period="daily",
            min_rent_months=3,
        )
        cleared = _clear_incompatible_fields(listing)
        assert "min_rent_months" in cleared
        assert listing.min_rent_months is None

    async def test_rule_p4_long_term_keeps_min_rent_months(
        self, db_session: AsyncSession
    ):
        """min_rent_months survives P4 when rent_period='long_term'."""
        from app.api.v1.listings import _clear_incompatible_fields

        listing = Listing(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=500,
            currency=Currency.USD,
            rooms=2,
            area=55.0,
            floor=4,
            total_floors=12,
            building_type="new",
            condition="euro",
            is_furnished=True,
            rent_period="long_term",
            min_rent_months=12,
        )
        cleared = _clear_incompatible_fields(listing)
        assert "min_rent_months" not in cleared
        assert listing.min_rent_months == 12

    async def test_rule_p2_idempotent_on_pristine_rent_listing(
        self, db_session: AsyncSession
    ):
        """A correctly configured rental triggers zero clears."""
        from app.api.v1.listings import _clear_incompatible_fields

        listing = Listing(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=600,
            currency=Currency.USD,
            rooms=2,
            area=55.0,
            floor=4,
            total_floors=9,
            building_type="secondary",
            condition="cosmetic",
            is_furnished=True,
            rent_period="long_term",
            deposit=1200,
            min_rent_months=6,
            rent_payment=["cash", "payme"],
        )
        cleared = _clear_incompatible_fields(listing)
        assert cleared == []


class TestRentPeriodRequired:
    """Rule: rent_period is mandatory when type='rent'."""

    async def test_helper_raises_when_rent_without_rent_period(
        self, db_session: AsyncSession
    ):
        from app.api.v1.listings import _validate_required_fields
        from app.core.exceptions import BadRequestException

        listing = Listing(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=800,
            currency=Currency.USD,
            rooms=2,
            area=50.0,
            floor=3,
            total_floors=9,
            building_type="secondary",
            condition="euro",
            is_furnished=True,
            region="toshkent_shahri",
            district="mirzo_ulugbek",
            latitude=41.3,
            longitude=69.3,
            # rent_period omitted on purpose
        )
        with pytest.raises(BadRequestException) as exc:
            _validate_required_fields(listing)
        assert "rent_period" in str(exc.value)

    async def test_helper_raises_long_term_without_min_rent_months(
        self, db_session: AsyncSession
    ):
        from app.api.v1.listings import _validate_required_fields
        from app.core.exceptions import BadRequestException

        listing = Listing(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=800,
            currency=Currency.USD,
            rooms=2,
            area=50.0,
            floor=3,
            total_floors=9,
            building_type="secondary",
            condition="euro",
            is_furnished=True,
            rent_period="long_term",
            region="toshkent_shahri",
            district="mirzo_ulugbek",
            latitude=41.3,
            longitude=69.3,
            # min_rent_months omitted on purpose
        )
        with pytest.raises(BadRequestException) as exc:
            _validate_required_fields(listing)
        assert "min_rent_months" in str(exc.value)

    async def test_helper_passes_for_daily_rent_without_min_rent_months(
        self, db_session: AsyncSession
    ):
        """Daily rentals do NOT require min_rent_months."""
        from app.api.v1.listings import _validate_required_fields

        listing = Listing(
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=80,
            currency=Currency.USD,
            rooms=1,
            area=35.0,
            floor=1,
            total_floors=5,
            building_type="new",
            condition="euro",
            is_furnished=True,
            rent_period="daily",
            region="toshkent_shahri",
            district="mirzo_ulugbek",
            latitude=41.3,
            longitude=69.3,
        )
        # Should NOT raise
        _validate_required_fields(listing)

    async def test_helper_passes_for_sale_without_rent_period(
        self, db_session: AsyncSession
    ):
        """Sale listings don't need rent_period at all."""
        from app.api.v1.listings import _validate_required_fields

        listing = Listing(
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            price=100000,
            currency=Currency.USD,
            rooms=3,
            area=80.0,
            floor=5,
            total_floors=12,
            building_type="new",
            condition="euro",
            is_furnished=True,
            region="toshkent_shahri",
            district="mirzo_ulugbek",
            latitude=41.3,
            longitude=69.3,
        )
        _validate_required_fields(listing)


class TestPatchTypeTransition:
    """HTTP-layer transition coverage for PATCH that toggles sell↔rent."""

    async def _make_sale_listing(
        self, db_session: AsyncSession, test_seller
    ) -> Listing:
        listing = Listing(
            id=uuid4(),
            seller_id=test_seller.id,
            title="Sale for transition",
            type=ListingType.SELL,
            property_type=PropertyType.APARTMENT,
            price=70000,
            currency=Currency.USD,
            rooms=2,
            area=60.0,
            floor=3,
            total_floors=9,
            building_type="new",
            condition="euro",
            is_furnished=True,
            mortgage_ok=True,
            installment_ok=True,
            halol_ok=False,
            deed_type="cadastre",
            region="toshkent_shahri",
            district="mirzo_ulugbek",
            latitude=41.3,
            longitude=69.3,
            phone="+998901234567",
            status=ListingStatus.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
            source_type=SourceType.MANUAL,
        )
        db_session.add(listing)
        await db_session.commit()
        await db_session.refresh(listing)
        return listing

    async def test_patch_sell_to_rent_wipes_sale_finance_and_accepts_rent_period(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seller_headers,
        test_seller,
    ):
        listing = await self._make_sale_listing(db_session, test_seller)
        patch = {
            "type": "rent",
            "rent_period": "long_term",
            "min_rent_months": 6,
            "deposit": 1200,
        }
        resp = await client.patch(
            f"/api/v1/listings/{listing.id}", json=patch, headers=seller_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "rent"
        assert body["rent_period"] == "long_term"
        assert body["min_rent_months"] == 6
        assert body["deposit"] == 1200
        # Sale-finance must be cleared
        assert body["mortgage_ok"] is False
        assert body["installment_ok"] is False
        assert body["halol_ok"] is False
        assert body["deed_type"] is None

    async def test_patch_rent_to_sell_wipes_rent_group_and_accepts_deed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        seller_headers,
        test_seller,
    ):
        # Start from a rental listing.
        rental = Listing(
            id=uuid4(),
            seller_id=test_seller.id,
            type=ListingType.RENT,
            property_type=PropertyType.APARTMENT,
            price=500,
            currency=Currency.USD,
            rooms=2,
            area=55.0,
            floor=3,
            total_floors=9,
            building_type="secondary",
            condition="euro",
            is_furnished=True,
            rent_period="long_term",
            deposit=1000,
            utilities_incl=True,
            min_rent_months=12,
            allowed_students=True,
            allowed_pets=False,
            rent_payment=["cash", "payme"],
            region="toshkent_shahri",
            district="mirzo_ulugbek",
            latitude=41.3,
            longitude=69.3,
            phone="+998901234567",
            status=ListingStatus.ACTIVE,
            moderation_status=ModerationStatus.APPROVED,
            source_type=SourceType.MANUAL,
        )
        db_session.add(rental)
        await db_session.commit()
        await db_session.refresh(rental)

        patch = {"type": "sell", "mortgage_ok": True, "deed_type": "cadastre"}
        resp = await client.patch(
            f"/api/v1/listings/{rental.id}", json=patch, headers=seller_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["type"] == "sell"
        assert body["mortgage_ok"] is True
        assert body["deed_type"] == "cadastre"
        # Rent-group must be cleared
        for field in (
            "rent_period",
            "deposit",
            "utilities_incl",
            "min_rent_months",
            "allowed_students",
            "allowed_pets",
            "rent_payment",
        ):
            assert body[field] in (None, []), f"{field} should be cleared on → sell"

    async def test_create_rent_without_rent_period_returns_400(
        self, client: AsyncClient, seller_headers
    ):
        payload = {
            "title": "Bad rent",
            "description": "missing rent_period",
            "type": "rent",
            "property_type": "apartment",
            "price": 500,
            "currency": "USD",
            "rooms": 2,
            "area": 55.0,
            "floor": 3,
            "total_floors": 9,
            "building_type": "secondary",
            "condition": "euro",
            "is_furnished": True,
            "region": "toshkent_shahri",
            "district": "mirzo_ulugbek",
            "latitude": 41.3,
            "longitude": 69.3,
            "phone": "+998901234567",
            "images": [{"original_url": "http://example.com/img.jpg", "position": 0}],
            # rent_period omitted on purpose
        }
        resp = await client.post(
            "/api/v1/listings", json=payload, headers=seller_headers
        )
        assert resp.status_code == 400
        assert "rent_period" in resp.json().get("detail", "")

    async def test_create_long_term_rent_without_min_rent_months_returns_400(
        self, client: AsyncClient, seller_headers
    ):
        payload = {
            "title": "Long term no min",
            "description": "needs min_rent_months",
            "type": "rent",
            "property_type": "apartment",
            "price": 500,
            "currency": "USD",
            "rooms": 2,
            "area": 55.0,
            "floor": 3,
            "total_floors": 9,
            "building_type": "secondary",
            "condition": "euro",
            "is_furnished": True,
            "rent_period": "long_term",
            "region": "toshkent_shahri",
            "district": "mirzo_ulugbek",
            "latitude": 41.3,
            "longitude": 69.3,
            "phone": "+998901234567",
            "images": [{"original_url": "http://example.com/img.jpg", "position": 0}],
        }
        resp = await client.post(
            "/api/v1/listings", json=payload, headers=seller_headers
        )
        assert resp.status_code == 400
        assert "min_rent_months" in resp.json().get("detail", "")
