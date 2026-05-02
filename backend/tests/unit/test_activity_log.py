"""Activity-log receiver unit tests.

Thin endpoint — validates the Pydantic shape + allowed actions. Full
HTTP round-trip is not exercised here (no DB writes to mock), but
the shape validation is the only thing that could 400 at the wire.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.api.v1.activity_log import ActivityLogPayload, _ALLOWED_ACTIONS

pytestmark = pytest.mark.unit


class TestActivityLogPayload:
    def test_minimum_valid_payload(self):
        m = ActivityLogPayload(action="like")
        assert m.action == "like"
        assert m.listing_id is None
        assert m.query is None
        assert m.filters is None

    def test_full_payload_preserved(self):
        lid = uuid4()
        m = ActivityLogPayload(
            action="save_search",
            listing_id=lid,
            query="apartment 2-room",
            filters={"deal_type": "rent", "price_max": 500},
            duration_ms=1234,
            property_type="apartment",
        )
        assert m.action == "save_search"
        assert m.listing_id == lid
        assert m.query == "apartment 2-room"
        assert m.filters == {"deal_type": "rent", "price_max": 500}
        assert m.duration_ms == 1234
        assert m.property_type == "apartment"

    def test_unknown_action_accepted_but_flagged(self):
        # Forward-compat: unknown actions don't 400; the route logs
        # them at WARNING level so ops notices.
        m = ActivityLogPayload(action="future_event")
        assert m.action == "future_event"
        assert "future_event" not in _ALLOWED_ACTIONS

    def test_action_length_enforced(self):
        with pytest.raises(Exception):
            ActivityLogPayload(action="x" * 31)

    def test_query_length_enforced(self):
        with pytest.raises(Exception):
            ActivityLogPayload(action="search", query="x" * 201)

    def test_duration_ms_upper_bound(self):
        # 1 hour is the hard upper cap (prevents garbage from client bugs).
        ActivityLogPayload(action="view", duration_ms=3_600_000)
        with pytest.raises(Exception):
            ActivityLogPayload(action="view", duration_ms=3_600_001)

    def test_duration_ms_negative_rejected(self):
        with pytest.raises(Exception):
            ActivityLogPayload(action="view", duration_ms=-1)

    def test_allowed_actions_set_stable(self):
        # Guard against silently widening the allowlist — every change
        # to this set should be a conscious decision.
        assert _ALLOWED_ACTIONS == {
            "like",
            "unlike",
            "view",
            "search",
            "save_search",
        }
