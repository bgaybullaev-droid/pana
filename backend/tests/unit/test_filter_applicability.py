"""Unit tests for the T-018 filter applicability engine.

Tests the `_filter_is_applicable` gate in isolation — no DB, no HTTP.
Confirms the silent-drop rule respects the visibility matrix and handles
partial pins (pt only, dt only, or neither) correctly.
"""

import pytest

from app.api.v1.listings import (
    _ALWAYS_APPLICABLE,
    _FILTER_TO_FIELD,
    _filter_is_applicable,
)

pytestmark = pytest.mark.unit


class TestAlwaysApplicable:
    @pytest.mark.parametrize(
        "key",
        [
            "q",
            "type",
            "property_type",
            "region",
            "district",
            "price_min",
            "price_max",
            "sort_by",
            "sort_order",
        ],
    )
    def test_always_true_regardless_of_pt_dt(self, key):
        # Pinned combo
        assert _filter_is_applicable(key, "apartment", "rent") is True
        assert _filter_is_applicable(key, "land", "sell") is True
        # No combo
        assert _filter_is_applicable(key, None, None) is True


class TestRentGroupDroppedOnSell:
    """Rent filters silently drop when caller pins type=sell."""

    @pytest.mark.parametrize(
        "key",
        [
            "rent_period",
            "utilities_incl",
            "min_rent_months",
            "allowed_students",
            "allowed_pets",
            "rent_payment",
            "deposit_min",
            "deposit_max",
        ],
    )
    def test_rent_filter_dropped_on_sell(self, key):
        assert _filter_is_applicable(key, "apartment", "sell") is False
        assert _filter_is_applicable(key, "house", "sell") is False
        assert _filter_is_applicable(key, "commercial", "sell") is False
        assert _filter_is_applicable(key, "land", "sell") is False

    @pytest.mark.parametrize(
        "key",
        [
            "rent_period",
            "utilities_incl",
            "min_rent_months",
            "deposit_min",
        ],
    )
    def test_rent_filter_applies_on_rent(self, key):
        assert _filter_is_applicable(key, "apartment", "rent") is True
        assert _filter_is_applicable(key, "house", "rent") is True
        assert _filter_is_applicable(key, "commercial", "rent") is True


class TestSaleFinanceDroppedOnRent:
    """Sale-finance filters silently drop when caller pins type=rent."""

    @pytest.mark.parametrize(
        "key",
        ["mortgage_ok", "installment_ok", "halol_ok", "deed_type"],
    )
    def test_sale_filter_dropped_on_rent(self, key):
        assert _filter_is_applicable(key, "apartment", "rent") is False
        assert _filter_is_applicable(key, "house", "rent") is False
        assert _filter_is_applicable(key, "commercial", "rent") is False
        # land×rent is illegal but matrix says empty; filter still drops.
        assert _filter_is_applicable(key, "land", "rent") is False

    @pytest.mark.parametrize(
        "key",
        ["mortgage_ok", "installment_ok", "halol_ok", "deed_type"],
    )
    def test_sale_filter_applies_on_sell(self, key):
        # Sale-finance group is visible on every property_type for type=sell.
        for pt in ("apartment", "house", "commercial", "land"):
            assert _filter_is_applicable(key, pt, "sell") is True


class TestPropertyTypeGating:
    def test_kitchen_area_is_apartment_only_concept(self):
        # kitchen_area isn't a filter key but living_area-range-ish logic
        # applies via rooms/floor. Test rooms: commercial hides rooms.
        assert _filter_is_applicable("rooms", "commercial", "sell") is False
        assert _filter_is_applicable("rooms", "commercial", "rent") is False
        assert _filter_is_applicable("rooms", "apartment", "sell") is True
        assert _filter_is_applicable("rooms", "house", "rent") is True

    def test_floor_not_visible_on_house(self):
        # Per matrix §2.1, house hides floor.
        assert _filter_is_applicable("floor_min", "house", "sell") is False
        assert _filter_is_applicable("floor_max", "house", "rent") is False
        assert _filter_is_applicable("floor_min", "apartment", "sell") is True
        assert _filter_is_applicable("floor_min", "commercial", "sell") is True

    def test_land_area_only_visible_on_house_or_land(self):
        assert _filter_is_applicable("land_area_min", "apartment", "sell") is False
        assert _filter_is_applicable("land_area_min", "commercial", "sell") is False
        assert _filter_is_applicable("land_area_min", "house", "sell") is True
        assert _filter_is_applicable("land_area_min", "land", "sell") is True


class TestPartialPinWidens:
    """When only pt (or dt, or neither) is pinned, filter applies if visible
    in AT LEAST ONE matching combo."""

    def test_rent_filter_applies_when_only_pt_given(self):
        # apartment without dt pinned → rent filter still applies (visible
        # in apartment_rent).
        assert _filter_is_applicable("rent_period", "apartment", None) is True
        # commercial without dt → rent filter applies (commercial_rent has it).
        assert _filter_is_applicable("rent_period", "commercial", None) is True
        # land without dt → rent filter applies too (land × rent is legal).
        assert _filter_is_applicable("rent_period", "land", None) is True

    def test_mortgage_applies_when_only_pt_given(self):
        # Sale-finance is in the allowlist for every property_type on sell.
        for pt in ("apartment", "house", "commercial", "land"):
            assert _filter_is_applicable("mortgage_ok", pt, None) is True

    def test_filter_applies_when_only_dt_given(self):
        # type=rent without property_type → rent_period applies (visible in
        # apartment/house/commercial × rent).
        assert _filter_is_applicable("rent_period", None, "rent") is True
        # type=sell → rent_period drops (no combo has it on sell).
        assert _filter_is_applicable("rent_period", None, "sell") is False
        # mortgage_ok is sell-only, so:
        assert _filter_is_applicable("mortgage_ok", None, "sell") is True
        assert _filter_is_applicable("mortgage_ok", None, "rent") is False

    def test_neither_pinned_filters_always_pass(self):
        # No caller constraint → widest interpretation; filter still applies.
        for key in (
            "rent_period",
            "mortgage_ok",
            "rooms",
            "floor_min",
            "land_area_min",
        ):
            assert _filter_is_applicable(key, None, None) is True


class TestMappingCoverage:
    # price_per_sqm was dropped from the commercial base in the Phase-1 UX
    # pass, but its filter mapping stays: old saved searches may still carry
    # price_per_sqm_min/max, and the mapping makes _filter_is_applicable
    # silently drop them (removing it would hit the default-open branch and
    # make the filter apply everywhere instead).
    _RETIRED_COLUMNS = frozenset({"price_per_sqm"})

    def test_every_mapped_filter_maps_to_a_known_matrix_field(self):
        """Every filter in _FILTER_TO_FIELD must correspond to a field that
        appears in the visibility matrix for at least one combo (or be an
        explicitly retired column kept for legacy saved searches)."""
        from app.api.v1.listings import _VISIBILITY_MATRIX

        all_visible_fields: set[str] = set()
        for fields in _VISIBILITY_MATRIX.values():
            all_visible_fields |= set(fields)
        # Fields not in any matrix combo (shouldn't exist today):
        orphans = [
            (fk, field)
            for fk, field in _FILTER_TO_FIELD.items()
            if field not in all_visible_fields
            and field not in self._RETIRED_COLUMNS
        ]
        assert not orphans, (
            f"Filter keys mapped to columns that aren't in the visibility "
            f"matrix: {orphans}"
        )

    def test_always_applicable_set_does_not_overlap_field_map(self):
        """A filter can't be both always-applicable and matrix-gated."""
        overlap = _ALWAYS_APPLICABLE & set(_FILTER_TO_FIELD.keys())
        assert (
            not overlap
        ), f"Filters in both _ALWAYS_APPLICABLE and _FILTER_TO_FIELD: {overlap}"
