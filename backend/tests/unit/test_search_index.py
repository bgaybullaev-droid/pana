"""PR8 — Meilisearch index mapping + attribute-list unit tests.

Pure in-memory tests; no network / Meili client required. Verifies the
document mapping shape and that filterable/sortable/searchable attribute
lists stay in lockstep with the PR3 filter engine + PR4 facet dimensions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from app.db.models import (
    Currency,
    Listing,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
    SourceType,
)
from app.services.search_index import (
    FILTERABLE_ATTRIBUTES,
    INDEX_NAME,
    SEARCHABLE_ATTRIBUTES,
    SORTABLE_ATTRIBUTES,
    _enum_value,
    _map_listing_to_document,
    delete_listing,
    index_listing,
)

pytestmark = pytest.mark.unit


def _mk(**over) -> Listing:
    defaults = dict(
        id=uuid4(),
        type=ListingType.SELL,
        property_type=PropertyType.APARTMENT,
        status=ListingStatus.ACTIVE,
        moderation_status=ModerationStatus.APPROVED,
        source_type=SourceType.MANUAL,
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
        title="Nice apt",
        description="3-комн",
        address="Test Street 1",
        latitude=41.3,
        longitude=69.3,
        mortgage_ok=False,
        installment_ok=False,
        halol_ok=False,
        created_at=datetime(2026, 4, 14, 12, 0, 0),
    )
    defaults.update(over)
    return Listing(**defaults)


# ─────────────────────────────────────────────────────────────────────
# Document mapping
# ─────────────────────────────────────────────────────────────────────


class TestMapping:
    def test_enum_value_unwraps_to_uppercase_name(self):
        assert _enum_value(ListingType.SELL) == "SELL"
        assert _enum_value(ListingType.RENT) == "RENT"
        assert _enum_value(PropertyType.LAND) == "LAND"
        assert _enum_value(Currency.USD) == "USD"
        assert _enum_value(None) is None

    def test_primary_key_is_string_uuid(self):
        listing = _mk()
        doc = _map_listing_to_document(listing)
        assert isinstance(doc["id"], str)
        assert doc["id"] == str(listing.id)

    def test_enums_stored_as_uppercase_strings(self):
        doc = _map_listing_to_document(_mk())
        assert doc["type"] == "SELL"
        assert doc["property_type"] == "APARTMENT"
        assert doc["status"] == "ACTIVE"
        assert doc["moderation_status"] == "APPROVED"
        assert doc["currency"] == "USD"

    def test_scalars_preserve_raw_types(self):
        doc = _map_listing_to_document(
            _mk(rooms=3, area=75.5, price=100000, rent_period="long_term")
        )
        assert doc["rooms"] == 3
        assert doc["area"] == 75.5
        assert doc["price"] == 100000
        assert doc["rent_period"] == "long_term"

    def test_arrays_are_arrays_never_none(self):
        with_arrays = _map_listing_to_document(
            _mk(amenities=["tv", "ac"], rent_payment=["cash"])
        )
        assert with_arrays["amenities"] == ["tv", "ac"]
        assert with_arrays["rent_payment"] == ["cash"]

        without = _map_listing_to_document(
            _mk(amenities=None, rent_payment=None, nearby_amenities=None)
        )
        # None → [] for Meili (array fields must be consistently typed).
        assert without["amenities"] == []
        assert without["rent_payment"] == []
        assert without["nearby_amenities"] == []

    def test_sale_finance_booleans_always_bool(self):
        doc = _map_listing_to_document(
            _mk(mortgage_ok=True, installment_ok=False, halol_ok=True)
        )
        assert doc["mortgage_ok"] is True
        assert doc["installment_ok"] is False
        assert doc["halol_ok"] is True

    def test_created_at_is_iso_string(self):
        doc = _map_listing_to_document(_mk(created_at=datetime(2026, 4, 14, 12, 30, 0)))
        assert doc["created_at"] == "2026-04-14T12:30:00"

    def test_null_created_at_preserved(self):
        doc = _map_listing_to_document(_mk(created_at=None))
        assert doc["created_at"] is None


# ─────────────────────────────────────────────────────────────────────
# Attribute lists — coverage contract
# ─────────────────────────────────────────────────────────────────────


class TestAttributeLists:
    """Filterable/sortable lists must cover every field PR3/PR4 expect.
    Missing entries here → Meilisearch rejects queries post-switchover."""

    REQUIRED_FILTERABLE = {
        "type",
        "property_type",
        "region",
        "district",
        "price",
        "rooms",
        "area",
        "land_area",
        "rent_period",
        "mortgage_ok",
        "installment_ok",
        "halol_ok",
        "amenities",
        "rent_payment",
    }

    REQUIRED_SORTABLE = {"price", "created_at"}

    def test_all_spec_fields_are_filterable(self):
        missing = self.REQUIRED_FILTERABLE - set(FILTERABLE_ATTRIBUTES)
        assert not missing, f"missing from FILTERABLE_ATTRIBUTES: {missing}"

    def test_all_spec_fields_are_sortable(self):
        missing = self.REQUIRED_SORTABLE - set(SORTABLE_ATTRIBUTES)
        assert not missing, f"missing from SORTABLE_ATTRIBUTES: {missing}"

    def test_no_duplicates_in_attribute_lists(self):
        for name, attrs in (
            ("FILTERABLE", FILTERABLE_ATTRIBUTES),
            ("SORTABLE", SORTABLE_ATTRIBUTES),
            ("SEARCHABLE", SEARCHABLE_ATTRIBUTES),
        ):
            assert len(attrs) == len(set(attrs)), f"{name} has duplicates"

    def test_every_filterable_key_is_in_the_document(self):
        """No filterable attribute may reference a field we don't map in."""
        doc = _map_listing_to_document(_mk())
        missing = [a for a in FILTERABLE_ATTRIBUTES if a not in doc]
        assert not missing, f"filterable attrs absent from mapped document: {missing}"

    def test_every_sortable_key_is_in_the_document(self):
        doc = _map_listing_to_document(_mk())
        missing = [a for a in SORTABLE_ATTRIBUTES if a not in doc]
        assert not missing, f"sortable attrs absent from mapped document: {missing}"

    def test_every_searchable_key_is_in_the_document(self):
        doc = _map_listing_to_document(_mk())
        missing = [a for a in SEARCHABLE_ATTRIBUTES if a not in doc]
        assert not missing, f"searchable attrs absent from mapped document: {missing}"

    def test_index_name_is_listings(self):
        # Guards against accidental rename; downstream scripts rely on this.
        assert INDEX_NAME == "listings"


# ─────────────────────────────────────────────────────────────────────
# Safe-fallback contract — when Meili is unavailable, writes succeed
# ─────────────────────────────────────────────────────────────────────


class TestSafeFallback:
    """index_listing / delete_listing must NEVER raise. They may return
    False if Meili is unreachable (which is the default in unit test env
    — no Meili process is running), but they cannot poison the caller's
    write transaction by propagating an exception."""

    def test_index_listing_returns_bool(self):
        result = index_listing(_mk())
        assert isinstance(result, bool)

    def test_delete_listing_returns_bool(self):
        result = delete_listing(uuid4())
        assert isinstance(result, bool)

    def test_index_listing_does_not_raise_on_meili_unreachable(self):
        # Smoke: host will likely be unreachable in CI — must not raise.
        try:
            index_listing(_mk())
        except Exception as exc:
            pytest.fail(f"index_listing raised unexpectedly: {exc}")

    def test_delete_listing_does_not_raise(self):
        try:
            delete_listing(uuid4())
        except Exception as exc:
            pytest.fail(f"delete_listing raised unexpectedly: {exc}")
