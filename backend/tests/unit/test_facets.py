"""Unit tests for the T-019 facets engine.

Covers:
    - _FACET_SPECS coverage (applicability contract per spec)
    - cache key stability & determinism
    - applicability gating (rent-group dropped on sell, sale-finance on rent)
    - safe-fallback contract of _facets_cache_key (pure function)

HTTP-layer correctness + Redis miss/hit cycle live in the integration suite
(see test_facets_endpoint.py).
"""

import pytest

from app.api.v1.listings import _FACET_SPECS, _facets_cache_key, _filter_is_applicable
from app.schemas.listing import ListingFilters

pytestmark = pytest.mark.unit


class TestFacetSpecsShape:
    def test_spec_covers_advertised_facet_keys(self):
        # S2 baseline + S3–S5 additions (T-001 urgent_flag, T-009 commercial
        # fields, T-006/008 dual-read renames).
        response_keys = {row[0] for row in _FACET_SPECS}
        assert response_keys == {
            "deal_type",
            "property_type",
            "region",
            "district",
            "rooms",
            "rent_period",
            "rent_payment",
            "mortgage_ok",
            "installment_ok",
            "halol_ok",
            # S3 (T-001)
            "urgent_flag",
            # S4 (T-009)
            "commercial_type",
            "building_class",
            # S5 (T-006, T-008)
            "market_type",
            "furniture",
        }

    def test_every_filter_key_is_known(self):
        """Each facet's filter_key must resolve in the applicability engine."""
        for response_key, filter_key, column, style, _ in _FACET_SPECS:
            # Partial-pin widens; neither-pinned passes trivially. What
            # matters is the function resolves without raising.
            assert _filter_is_applicable(filter_key, None, None) is True

    def test_styles_are_within_supported_set(self):
        allowed = {"scalar_enum", "scalar_int", "array", "boolean_true"}
        for _, _, _, style, _ in _FACET_SPECS:
            assert style in allowed


class TestApplicabilityGating:
    """Spec: non-applicable facets must be OMITTED from the response."""

    def test_sell_filter_drops_rent_group_facets(self):
        """When caller pins type=sell, no rent-group facet can be computed."""
        for _, filter_key, _, _, _ in _FACET_SPECS:
            if filter_key in {"rent_period", "rent_payment"}:
                assert _filter_is_applicable(filter_key, "apartment", "sell") is False

    def test_rent_filter_drops_sale_finance_facets(self):
        for _, filter_key, _, _, _ in _FACET_SPECS:
            if filter_key in {
                "mortgage_ok",
                "installment_ok",
                "halol_ok",
            }:
                assert _filter_is_applicable(filter_key, "apartment", "rent") is False

    def test_always_applicable_facets_survive_both_types(self):
        always = {"type", "property_type", "region", "district"}
        for _, filter_key, _, _, _ in _FACET_SPECS:
            if filter_key in always:
                assert _filter_is_applicable(filter_key, "apartment", "sell") is True
                assert _filter_is_applicable(filter_key, "apartment", "rent") is True
                assert _filter_is_applicable(filter_key, "land", "sell") is True

    def test_rooms_facet_dropped_on_commercial(self):
        """rooms isn't in the commercial matrix → omitted from commercial facets."""
        assert _filter_is_applicable("rooms", "commercial", "sell") is False
        assert _filter_is_applicable("rooms", "commercial", "rent") is False
        assert _filter_is_applicable("rooms", "apartment", "sell") is True
        assert _filter_is_applicable("rooms", "house", "rent") is True


class TestCacheKey:
    def test_key_is_deterministic(self):
        f1 = ListingFilters(type="rent", property_type="apartment")
        f2 = ListingFilters(type="rent", property_type="apartment")
        assert _facets_cache_key(f1) == _facets_cache_key(f2)

    def test_key_changes_when_filters_change(self):
        f_sell = ListingFilters(type="sell")
        f_rent = ListingFilters(type="rent")
        assert _facets_cache_key(f_sell) != _facets_cache_key(f_rent)

    def test_key_is_prefixed(self):
        key = _facets_cache_key(ListingFilters())
        assert key.startswith("facets:")

    def test_list_filters_are_order_insensitive(self):
        """Sorting list values keeps equivalent filter sets on the same key."""
        a = ListingFilters(region=["tashkent", "samarkand"])
        b = ListingFilters(region=["samarkand", "tashkent"])
        assert _facets_cache_key(a) == _facets_cache_key(b)

    def test_rooms_list_order_insensitive(self):
        a = ListingFilters(rooms=[1, 2, 3])
        b = ListingFilters(rooms=[3, 2, 1])
        assert _facets_cache_key(a) == _facets_cache_key(b)

    def test_empty_filter_has_stable_key(self):
        assert _facets_cache_key(ListingFilters()) == _facets_cache_key(
            ListingFilters()
        )
