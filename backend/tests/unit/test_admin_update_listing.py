"""PR-F.3 — Admin-scoped listing edit helpers.

Pure-helper coverage:
    - `_diff_values` returns only changed keys; preserves null↔value
    - `_serialize_audit_value` coerces enums / UUIDs / datetimes to
      JSON-safe primitives

The full PATCH round-trip (auth, matrix gating, audit-row insert, Meili
reindex) lives in the integration suite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.v1.admin import _diff_values, _serialize_audit_value
from app.db.models import (
    Currency,
    ListingStatus,
    ListingType,
    ModerationStatus,
    PropertyType,
)

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────
# _diff_values
# ─────────────────────────────────────────────────────────────────────


class TestDiffValues:
    def test_returns_only_changed_keys(self):
        before = {"a": 1, "b": 2, "c": 3}
        after = {"a": 1, "b": 20, "c": 3}
        assert _diff_values(before, after) == {"b": 2}

    def test_null_to_value_detected(self):
        before = {"x": None}
        after = {"x": "present"}
        assert _diff_values(before, after) == {"x": None}

    def test_value_to_null_detected(self):
        before = {"x": "was set"}
        after = {"x": None}
        assert _diff_values(before, after) == {"x": "was set"}

    def test_no_change_returns_empty(self):
        snapshot = {"a": 1, "b": None, "c": "keep"}
        assert _diff_values(snapshot, snapshot) == {}

    def test_missing_key_in_after_treated_as_null(self):
        # When `after` omits a key, the diff should still capture the
        # before value (treat absent == None).
        before = {"a": "gone"}
        after = {}
        assert _diff_values(before, after) == {"a": "gone"}

    def test_empty_inputs(self):
        assert _diff_values({}, {}) == {}


# ─────────────────────────────────────────────────────────────────────
# _serialize_audit_value
# ─────────────────────────────────────────────────────────────────────


class TestSerializeAuditValue:
    def test_none_passthrough(self):
        assert _serialize_audit_value(None) is None

    def test_primitive_passthrough(self):
        assert _serialize_audit_value(42) == 42
        assert _serialize_audit_value("hello") == "hello"
        assert _serialize_audit_value(3.14) == 3.14
        assert _serialize_audit_value(True) is True

    def test_enum_unwrapped_to_value(self):
        assert _serialize_audit_value(ListingType.SELL) == "sell"
        assert _serialize_audit_value(PropertyType.APARTMENT) == "apartment"
        assert _serialize_audit_value(Currency.USD) == "USD"
        assert _serialize_audit_value(ListingStatus.ACTIVE) == "active"
        assert _serialize_audit_value(ModerationStatus.APPROVED) == "approved"

    def test_uuid_stringified(self):
        u = uuid4()
        assert _serialize_audit_value(u) == str(u)

    def test_datetime_stringified(self):
        ts = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
        out = _serialize_audit_value(ts)
        assert isinstance(out, str)
        assert "2026-04-25" in out

    def test_list_passthrough(self):
        assert _serialize_audit_value([1, 2, 3]) == [1, 2, 3]
        assert _serialize_audit_value(["cash", "click"]) == ["cash", "click"]

    def test_dict_passthrough(self):
        assert _serialize_audit_value({"k": "v"}) == {"k": "v"}
