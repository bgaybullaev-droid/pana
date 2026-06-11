"""Sprints 3-9 — execution regression tests.

Validates the surgical additions made by the consolidated Sprint 3-9
implementation:

    Sprint 3 — visibility matrix gains jk_name + metro_station;
               P5 region sub-gate clears metro_station outside Tashkent;
               required-field rule: city.
    Sprint 4 — commercial fields land in COMMERCIAL allowlist;
               required-field rule: commercial_type for type='commercial'.
    Sprint 5 — dual-read helpers accept either old or new field names,
               reject conflicts, and mirror both names on response.
    Sprint 6 — property-polish fields land in their property-type
               allowlists.
    Sprint 7 — Seller has trust_score / is_developer_verified;
               HousingComplex model exists and exposes jk_id linkage.
    Sprint 8 — slug column is part of the model + Meili filterable.
    Sprint 9 — no schema change; validator audit covers prior rules.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.api.v1.listings import (
    _CLEARING_VALUES,
    _VISIBILITY_MATRIX,
    _apply_dual_read_inputs,
    _apply_dual_read_response,
    _clear_incompatible_fields,
    _validate_required_fields,
)
from app.core.exceptions import BadRequestException
from app.db.models import (
    Currency,
    HousingComplex,
    Listing,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
    Seller,
    SourceType,
)
from app.services.search_index import (
    FILTERABLE_ATTRIBUTES,
    SEARCHABLE_ATTRIBUTES,
    _map_listing_to_document,
)

pytestmark = pytest.mark.unit


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
        city="Tashkent",
        latitude=41.3,
        longitude=69.3,
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
    )
    defaults.update(over)
    return Listing(**defaults)


# ─────────────────────────────────────────────────────────────────────
# Sprint 3 — location matrix + P5 region sub-gate + city required
# ─────────────────────────────────────────────────────────────────────


class TestSprint3LocationMatrix:
    # Phase-1 UX pass: jk_name removed from the house base — housing
    # complexes only apply to apartments.
    def test_jk_name_visible_on_apartment_only(self):
        for dt in ("sell", "rent"):
            assert "jk_name" in _VISIBILITY_MATRIX[("apartment", dt)]

    def test_jk_name_hidden_on_house_commercial_and_land(self):
        assert "jk_name" not in _VISIBILITY_MATRIX[("house", "sell")]
        assert "jk_name" not in _VISIBILITY_MATRIX[("commercial", "sell")]
        assert "jk_name" not in _VISIBILITY_MATRIX[("land", "sell")]

    def test_metro_station_visible_on_apartment_and_commercial(self):
        for pt in ("apartment", "commercial"):
            for dt in ("sell", "rent"):
                assert "metro_station" in _VISIBILITY_MATRIX[(pt, dt)]
        # House hides metro_station per blueprint §2.1
        assert "metro_station" not in _VISIBILITY_MATRIX[("house", "sell")]

    def test_p5_clears_metro_station_outside_tashkent(self):
        listing = _mk(
            region="samarqand_viloyati",
            metro_station="chilonzor",  # stale
        )
        cleared = _clear_incompatible_fields(listing)
        assert "metro_station" in cleared
        assert listing.metro_station is None

    def test_p5_keeps_metro_station_inside_tashkent(self):
        listing = _mk(
            region="toshkent_shahri",
            metro_station="chilonzor",
        )
        cleared = _clear_incompatible_fields(listing)
        assert "metro_station" not in cleared
        assert listing.metro_station == "chilonzor"

    def test_required_field_city_blocks_when_missing(self):
        listing = _mk(city=None)
        with pytest.raises(BadRequestException) as exc:
            _validate_required_fields(listing)
        assert "city" in str(exc.value)


# ─────────────────────────────────────────────────────────────────────
# Sprint 4 — commercial overhaul matrix + required commercial_type
# ─────────────────────────────────────────────────────────────────────


class TestSprint4Commercial:
    # Phase-1 UX pass: price_per_sqm dropped from the commercial base and
    # ceiling_height widened to apartment/house (no longer commercial-only).
    def test_commercial_fields_in_commercial_matrix(self):
        for f in (
            "commercial_type",
            "ceiling_height",
            "entrance",
            "parking_comm",
            "building_class",
        ):
            assert f in _VISIBILITY_MATRIX[("commercial", "sell")]
            assert f in _VISIBILITY_MATRIX[("commercial", "rent")]
            # Hidden everywhere else — except ceiling_height, which is
            # visible for all property types but land.
            if f != "ceiling_height":
                assert f not in _VISIBILITY_MATRIX[("apartment", "sell")]
                assert f not in _VISIBILITY_MATRIX[("house", "sell")]
        assert "ceiling_height" not in _VISIBILITY_MATRIX[("land", "sell")]

    def test_commercial_type_required_for_commercial_listings(self):
        listing = _mk(
            property_type=PropertyType.COMMERCIAL,
            rooms=None,  # commercial doesn't have rooms
            commercial_type=None,  # missing on purpose
        )
        with pytest.raises(BadRequestException) as exc:
            _validate_required_fields(listing)
        assert "commercial_type" in str(exc.value)


# ─────────────────────────────────────────────────────────────────────
# Sprint 5 — dual-read inputs + response mirroring
# ─────────────────────────────────────────────────────────────────────


class TestSprint5DualRead:
    def test_old_name_input_promoted_to_new_name(self):
        out = _apply_dual_read_inputs(
            {"building_type": "secondary", "is_furnished": True}
        )
        assert out["market_type"] == "secondary"
        assert out["furniture"] == "full"

    def test_new_name_input_passed_through_unchanged(self):
        out = _apply_dual_read_inputs({"market_type": "new", "furniture": "partial"})
        assert out["market_type"] == "new"
        assert out["furniture"] == "partial"

    def test_conflict_old_and_new_raises(self):
        with pytest.raises(BadRequestException):
            _apply_dual_read_inputs(
                {"building_type": "new", "market_type": "secondary"}
            )
        with pytest.raises(BadRequestException):
            _apply_dual_read_inputs({"is_furnished": True, "furniture": "none"})

    def test_response_mirrors_both_names(self):
        listing = _mk(
            market_type="new", furniture="full", building_type=None, is_furnished=None
        )
        out = _apply_dual_read_response(listing)
        assert out["market_type"] == "new"
        assert out["building_type"] == "new"
        assert out["furniture"] == "full"
        assert out["is_furnished"] is True

    def test_furniture_to_is_furnished_partial_means_true(self):
        listing = _mk(
            market_type=None, furniture="partial", building_type=None, is_furnished=None
        )
        out = _apply_dual_read_response(listing)
        assert out["is_furnished"] is True

    def test_furniture_none_means_is_furnished_false(self):
        listing = _mk(
            market_type=None, furniture="none", building_type=None, is_furnished=None
        )
        out = _apply_dual_read_response(listing)
        assert out["is_furnished"] is False


# ─────────────────────────────────────────────────────────────────────
# Sprint 6 — property polish matrix placement
# ─────────────────────────────────────────────────────────────────────


class TestSprint6Polish:
    def test_garage_basement_house_only(self):
        for f in ("garage", "basement"):
            assert f in _VISIBILITY_MATRIX[("house", "sell")]
            assert f in _VISIBILITY_MATRIX[("house", "rent")]
            assert f not in _VISIBILITY_MATRIX[("apartment", "sell")]
            assert f not in _VISIBILITY_MATRIX[("commercial", "sell")]
            assert f not in _VISIBILITY_MATRIX[("land", "sell")]

    def test_balcony_listing_subtype_floor_plan_apartment_only(self):
        for f in ("balcony", "listing_subtype", "floor_plan_url"):
            assert f in _VISIBILITY_MATRIX[("apartment", "sell")]
            assert f in _VISIBILITY_MATRIX[("apartment", "rent")]
            assert f not in _VISIBILITY_MATRIX[("house", "sell")]

    def test_buildings_exist_fence_land_shape_land_only(self):
        for f in ("buildings_exist", "fence", "land_shape"):
            assert f in _VISIBILITY_MATRIX[("land", "sell")]
            assert f not in _VISIBILITY_MATRIX[("apartment", "sell")]
            assert f not in _VISIBILITY_MATRIX[("house", "sell")]


# ─────────────────────────────────────────────────────────────────────
# Sprint 7 — Seller extensions + HousingComplex model
# ─────────────────────────────────────────────────────────────────────


class TestSprint7RolesMedia:
    def test_seller_has_trust_score_and_developer_flag(self):
        seller = Seller(
            id=uuid4(),
            user_id=uuid4(),
            phone="+998901234567",
        )
        # Defaults work even without explicit assignment in tests.
        assert hasattr(seller, "trust_score")
        assert hasattr(seller, "is_developer_verified")

    def test_housing_complex_model_exists_and_creates(self):
        hc = HousingComplex(id=uuid4(), name="Tashkent City")
        assert hc.name == "Tashkent City"

    def test_jk_id_in_listing_model(self):
        listing = _mk()
        # Just attribute-level check; FK enforcement happens at DB layer.
        assert hasattr(listing, "jk_id")


# ─────────────────────────────────────────────────────────────────────
# Sprint 8 — slug column + Meili indexing
# ─────────────────────────────────────────────────────────────────────


class TestSprint8Discoverability:
    def test_slug_in_listing_model(self):
        assert hasattr(_mk(), "slug")

    def test_slug_in_meili_filterable(self):
        assert "slug" in FILTERABLE_ATTRIBUTES

    def test_slug_in_indexed_document(self):
        listing = _mk(slug="great-apt-tashkent")
        doc = _map_listing_to_document(listing)
        assert doc["slug"] == "great-apt-tashkent"


# ─────────────────────────────────────────────────────────────────────
# Sprint 3-6 — Meili indexing parity + clearing-values coverage
# ─────────────────────────────────────────────────────────────────────


class TestMeiliIndexParity:
    def test_searchable_includes_landmark_jk_microdistrict(self):
        for f in ("landmark", "jk_name", "microdistrict"):
            assert f in SEARCHABLE_ATTRIBUTES

    def test_filterable_includes_all_new_fields(self):
        for f in (
            "city",
            "microdistrict",
            "jk_name",
            "metro_station",
            "urgent_flag",
            "commercial_type",
            "ceiling_height",
            "entrance",
            "parking_comm",
            "building_class",
            "market_type",
            "wall_material",
            "furniture",
            "garage",
            "basement",
            "buildings_exist",
            "fence",
            "land_shape",
            "balcony",
            "listing_subtype",
        ):
            assert f in FILTERABLE_ATTRIBUTES, f

    def test_document_carries_all_new_fields(self):
        listing = _mk(
            city="Tashkent",
            microdistrict="Yunusabad-12",
            jk_name="Tashkent City",
            landmark="opposite the metro",
            metro_station="chilonzor",
            urgent_flag=True,
            commercial_type=None,
            market_type="new",
            furniture="full",
            wall_material="brick",
            garage=None,
            balcony="loggia",
            listing_subtype="standard",
            floor_plan_url="https://example.com/plan.png",
        )
        doc = _map_listing_to_document(listing)
        assert doc["city"] == "Tashkent"
        assert doc["microdistrict"] == "Yunusabad-12"
        assert doc["jk_name"] == "Tashkent City"
        assert doc["landmark"] == "opposite the metro"
        assert doc["metro_station"] == "chilonzor"
        assert doc["urgent_flag"] is True
        assert doc["market_type"] == "new"
        assert doc["furniture"] == "full"
        assert doc["wall_material"] == "brick"
        assert doc["balcony"] == "loggia"

    def test_clearing_values_cover_all_field_keys(self):
        """All matrix-gated fields MUST have a canonical empty value, or
        _clear_incompatible_fields would KeyError on transition."""
        all_visible: set[str] = set()
        for fields in _VISIBILITY_MATRIX.values():
            all_visible |= set(fields)
        missing = [f for f in all_visible if f not in _CLEARING_VALUES]
        assert (
            not missing
        ), f"matrix references fields without clearing values: {missing}"


# ─────────────────────────────────────────────────────────────────────
# Sprint 9 — no schema; validator-audit regression net
# ─────────────────────────────────────────────────────────────────────


class TestSprint9PolishValidator:
    def test_full_required_field_set_on_apartment_sell(self):
        # Bare minimum apartment sell that should validate.
        listing = _mk()
        _validate_required_fields(listing)  # no raise

    def test_rent_listing_still_requires_rent_period(self):
        listing = _mk(type=ListingType.RENT, price=500, rent_period=None)
        with pytest.raises(BadRequestException) as exc:
            _validate_required_fields(listing)
        assert "rent_period" in str(exc.value)
