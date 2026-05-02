"""PR-A — NotificationSettings endpoint unit tests.

Covers the pure-helper surface of the new endpoint:
    - from_model projection from NotificationPreferences row
    - time_windows validator (allowlist + dedupe)
    - sources validator (allowlist + type check)
    - daily_limit range enforcement

HTTP round-trip + DB persistence live in the integration suite.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.api.v1.notification_settings import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from app.db.models import NotificationPreferences

pytestmark = pytest.mark.unit


def _prefs(**over) -> NotificationPreferences:
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        enabled=True,
        daily_limit=10,
        disabled_types=[],
        districts=[],
        property_types=[],
        listing_types=[],
        price_min=None,
        price_max=None,
        rooms=[],
        time_windows=["morning", "afternoon", "evening"],
        source_saved_searches=True,
        source_seller_follows=True,
        source_ai_recs=True,
        paused=False,
        updated_at=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
    )
    defaults.update(over)
    return NotificationPreferences(**defaults)


class TestFromModel:
    def test_default_row_projects_frontend_shape(self):
        out = NotificationSettingsResponse.from_model(_prefs())
        assert out.daily_limit == 10
        assert out.time_windows == ["morning", "afternoon", "evening"]
        assert out.sources == {
            "saved_searches": True,
            "seller_follows": True,
            "ai_recs": True,
        }
        assert out.paused is False

    def test_paused_user_projects_paused_true(self):
        out = NotificationSettingsResponse.from_model(_prefs(paused=True))
        assert out.paused is True

    def test_source_toggle_reflects_in_response(self):
        out = NotificationSettingsResponse.from_model(_prefs(source_ai_recs=False))
        assert out.sources["ai_recs"] is False
        assert out.sources["saved_searches"] is True

    def test_custom_time_windows_preserved(self):
        out = NotificationSettingsResponse.from_model(_prefs(time_windows=["morning"]))
        assert out.time_windows == ["morning"]

    def test_null_time_windows_normalizes_to_empty_list(self):
        # Some older rows may have NULL. from_model must not crash.
        out = NotificationSettingsResponse.from_model(_prefs(time_windows=None))
        assert out.time_windows == []


class TestTimeWindowsValidator:
    def test_valid_subset_accepted(self):
        m = NotificationSettingsUpdate(time_windows=["morning", "evening"])
        assert m.time_windows == ["morning", "evening"]

    def test_empty_list_accepted(self):
        # Empty list = no delivery; equivalent to paused. Must NOT 400.
        m = NotificationSettingsUpdate(time_windows=[])
        assert m.time_windows == []

    def test_invalid_element_rejected(self):
        with pytest.raises(Exception):
            NotificationSettingsUpdate(time_windows=["midnight"])

    def test_duplicates_deduped_preserving_order(self):
        m = NotificationSettingsUpdate(
            time_windows=["morning", "evening", "morning", "afternoon"]
        )
        assert m.time_windows == ["morning", "evening", "afternoon"]

    def test_none_passes_through(self):
        m = NotificationSettingsUpdate(time_windows=None)
        assert m.time_windows is None


class TestSourcesValidator:
    def test_all_three_sources_accepted(self):
        m = NotificationSettingsUpdate(
            sources={
                "saved_searches": True,
                "seller_follows": False,
                "ai_recs": True,
            }
        )
        assert m.sources == {
            "saved_searches": True,
            "seller_follows": False,
            "ai_recs": True,
        }

    def test_partial_sources_accepted(self):
        m = NotificationSettingsUpdate(sources={"ai_recs": False})
        assert m.sources == {"ai_recs": False}

    def test_unknown_source_key_rejected(self):
        with pytest.raises(Exception):
            NotificationSettingsUpdate(sources={"telegram": True})

    def test_non_boolean_value_rejected(self):
        # Pydantic v2 coerces truthy strings ("yes", "1") to bool, so we
        # exercise a value it will NOT coerce to boolean.
        with pytest.raises(Exception):
            NotificationSettingsUpdate(sources={"saved_searches": {"nested": 1}})


class TestDailyLimit:
    def test_valid_range_accepted(self):
        NotificationSettingsUpdate(daily_limit=0)
        NotificationSettingsUpdate(daily_limit=50)
        NotificationSettingsUpdate(daily_limit=100)

    def test_negative_rejected(self):
        with pytest.raises(Exception):
            NotificationSettingsUpdate(daily_limit=-1)

    def test_over_max_rejected(self):
        with pytest.raises(Exception):
            NotificationSettingsUpdate(daily_limit=101)


class TestPausedToggle:
    def test_paused_accepts_boolean(self):
        assert NotificationSettingsUpdate(paused=True).paused is True
        assert NotificationSettingsUpdate(paused=False).paused is False

    def test_paused_none_passes_through(self):
        assert NotificationSettingsUpdate(paused=None).paused is None
