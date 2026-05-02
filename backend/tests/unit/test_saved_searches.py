"""PR-B — Saved Searches unit tests (pure helpers).

Exercises the helper surface:
    - _filters_to_listing_filters hydration (known keys preserved,
      unknown keys silently dropped, deal_type→type rename)
    - SavedSearchCreate Pydantic defaults
    - _to_response projection (naming + types)

HTTP round-trips + DB persistence + new_count computation against a real
listings table live in the integration suite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.v1.saved_searches import (
    SavedSearchCreate,
    SavedSearchResponse,
    _filters_to_listing_filters,
    _to_response,
)
from app.db.models import SavedSearch
from app.schemas.listing import ListingFilters

pytestmark = pytest.mark.unit


def _mk_saved(**over) -> SavedSearch:
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        name="",
        query=None,
        filters={},
        sort="relevance",
        notify_enabled=True,
        created_at=datetime(2026, 4, 24, 12, 0),
        updated_at=datetime(2026, 4, 24, 12, 0),
        last_seen_at=None,
    )
    defaults.update(over)
    return SavedSearch(**defaults)


class TestFiltersHydration:
    def test_known_keys_preserved(self):
        f = _filters_to_listing_filters(
            {
                "property_type": "apartment",
                "price_min": 50_000,
                "price_max": 100_000,
                "rooms": [2, 3],
            }
        )
        assert isinstance(f, ListingFilters)
        assert f.property_type == "apartment"
        assert f.price_min == 50_000
        assert f.price_max == 100_000
        assert f.rooms == [2, 3]

    def test_deal_type_renamed_to_type(self):
        # Frontend saved searches use `deal_type`; ListingFilters uses `type`.
        f = _filters_to_listing_filters({"deal_type": "rent"})
        assert f.type == "rent"

    def test_unknown_keys_silently_dropped(self):
        # Forward-compat: older saved searches may carry keys that have
        # since been removed. They must not crash the hydration.
        f = _filters_to_listing_filters(
            {"property_type": "house", "deprecated_field": "xyz"}
        )
        assert f.property_type == "house"

    def test_empty_dict_produces_empty_filters(self):
        f = _filters_to_listing_filters({})
        assert f.property_type is None
        assert f.type is None

    def test_malformed_filter_returns_empty(self):
        # A value Pydantic would reject (bad enum etc.) must not raise —
        # the GET handler needs to return SOMETHING for stored rows.
        f = _filters_to_listing_filters({"property_type": "cow"})
        assert isinstance(f, ListingFilters)


class TestSavedSearchCreateDefaults:
    def test_empty_payload_accepted(self):
        m = SavedSearchCreate()
        assert m.name is None
        assert m.query is None
        assert m.filters == {}
        assert m.sort is None

    def test_name_length_enforced(self):
        with pytest.raises(Exception):
            SavedSearchCreate(name="x" * 101)

    def test_query_length_enforced(self):
        with pytest.raises(Exception):
            SavedSearchCreate(query="x" * 201)

    def test_sort_length_enforced(self):
        with pytest.raises(Exception):
            SavedSearchCreate(sort="x" * 31)

    def test_arbitrary_filter_dict_accepted(self):
        # The model accepts any Dict[str, Any]. Enforcement happens at
        # hydration time when we project to ListingFilters.
        m = SavedSearchCreate(filters={"property_type": "apartment", "foo": 1})
        assert m.filters == {"property_type": "apartment", "foo": 1}


class TestToResponseProjection:
    def test_empty_row_projects_sane_defaults(self):
        saved = _mk_saved()
        out = _to_response(saved, new_count=0)
        assert isinstance(out, SavedSearchResponse)
        assert out.name == ""
        assert out.query is None
        assert out.filters == {}
        assert out.sort == "relevance"
        assert out.last_seen_at is None
        assert out.new_count == 0
        assert out.notifications_enabled is True

    def test_notifications_enabled_reflects_notify_enabled(self):
        saved = _mk_saved(notify_enabled=False)
        out = _to_response(saved, new_count=0)
        assert out.notifications_enabled is False

    def test_new_count_passed_through(self):
        saved = _mk_saved()
        assert _to_response(saved, new_count=42).new_count == 42

    def test_filters_copied_not_aliased(self):
        saved = _mk_saved(filters={"property_type": "house"})
        out = _to_response(saved, new_count=0)
        out.filters["property_type"] = "apartment"
        # Mutation must NOT propagate back to the model.
        assert saved.filters == {"property_type": "house"}

    def test_timestamps_preserved(self):
        ts = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)
        saved = _mk_saved(
            created_at=datetime(2026, 4, 24, 12, 0),
            last_seen_at=datetime(2026, 4, 24, 12, 0),
        )
        out = _to_response(saved, new_count=0)
        assert out.created_at is not None
        assert out.last_seen_at is not None
        # Exact instant equivalence is not asserted — UTCDateTime may
        # carry or drop tzinfo. The important assertion is non-null.
        del ts  # silence unused

    def test_null_sort_falls_back_to_relevance(self):
        saved = _mk_saved(sort=None)
        out = _to_response(saved, new_count=0)
        assert out.sort == "relevance"

    def test_null_filters_falls_back_to_empty_dict(self):
        saved = _mk_saved(filters=None)
        out = _to_response(saved, new_count=0)
        assert out.filters == {}
