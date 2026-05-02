"""PR-I — Audit log admin endpoint unit tests.

Covers the pure pieces:
    - `_format_actor_name` fallback chain:
        first/last > username > None
    - `AuditLogEntryResponse` shape (defaults, from_attributes)

HTTP + SQL join + pagination logic live in the integration suite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.v1.admin import AuditLogEntryResponse, _format_actor_name

pytestmark = pytest.mark.unit


class TestFormatActorName:
    def test_first_and_last_combined(self):
        assert _format_actor_name("Jane", "Doe", None) == "Jane Doe"

    def test_first_only(self):
        assert _format_actor_name("Jane", None, "janedoe") == "Jane"

    def test_last_only(self):
        assert _format_actor_name(None, "Doe", "janedoe") == "Doe"

    def test_username_fallback_when_no_real_name(self):
        assert _format_actor_name(None, None, "janedoe") == "@janedoe"

    def test_empty_first_last_falls_through_to_username(self):
        # Empty strings (not None) must still fall through to username.
        # Defensive: DB columns may have "" instead of NULL.
        assert _format_actor_name("", "", "janedoe") == "@janedoe"

    def test_none_everywhere_returns_none(self):
        # Anonymous row (user_id NULL → join produces all-NULL actor).
        assert _format_actor_name(None, None, None) is None


class TestAuditLogEntryResponseShape:
    def test_required_fields_populate(self):
        now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
        entry = AuditLogEntryResponse(
            id=uuid4(),
            user_id=uuid4(),
            actor_name="Jane Doe",
            entity_type="listing",
            entity_id=uuid4(),
            action="approve",
            created_at=now,
        )
        assert entry.entity_type == "listing"
        assert entry.action == "approve"
        assert entry.old_values is None
        assert entry.new_values is None
        assert entry.ip_address is None
        assert entry.user_agent is None

    def test_json_fields_pass_through(self):
        entry = AuditLogEntryResponse(
            id=uuid4(),
            user_id=None,
            actor_name=None,
            entity_type="user",
            entity_id=uuid4(),
            action="reject",
            old_values={"approval_status": "pending"},
            new_values={"approval_status": "rejected", "notes": "spam"},
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
            created_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        )
        assert entry.old_values == {"approval_status": "pending"}
        assert entry.new_values == {
            "approval_status": "rejected",
            "notes": "spam",
        }
        assert entry.ip_address == "10.0.0.1"

    def test_anonymous_entry_allowed(self):
        # user_id + actor_name both None — e.g. system-triggered audit.
        entry = AuditLogEntryResponse(
            id=uuid4(),
            user_id=None,
            actor_name=None,
            entity_type="listing",
            entity_id=uuid4(),
            action="auto_expire",
            created_at=datetime(2026, 4, 25, tzinfo=timezone.utc),
        )
        assert entry.user_id is None
        assert entry.actor_name is None
