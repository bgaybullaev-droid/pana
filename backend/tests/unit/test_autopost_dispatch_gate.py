"""Unit tests for the Block D D4 autopost dispatch gate.

Covers ``_dispatch_autopost_for_status_change`` — specifically the
per-listing ``publish_to_channel`` opt-out that gates ONLY the publish
branch, leaving the mark-sold / delete branches untouched so an already
published post keeps its lifecycle in sync.

The domain function ``services/autopost.decide_transition`` is dead code
(no callers); the live dispatch path is this API-layer helper, so that is
what we test.
"""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.api.v1.listings import _dispatch_autopost_for_status_change
from app.db.models import ListingStatus

pytestmark = pytest.mark.unit


def _seller(**over):
    """A seller with a fully connected, verified, enabled channel."""
    base = dict(
        id=uuid4(),
        autopost_channel_id=-1001234567890,
        autopost_enabled=True,
        autopost_verified_at="2026-06-01T00:00:00Z",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _listing(**over):
    base = dict(
        id=uuid4(),
        status=ListingStatus.ACTIVE,
        publish_to_channel=True,
    )
    base.update(over)
    return SimpleNamespace(**base)


class TestPublishGate:
    """DRAFT -> ACTIVE transition routes through the publish branch."""

    def test_publishes_when_opted_in(self):
        with patch("app.workers.tasks.autopost.publish_listing_to_channel") as task:
            _dispatch_autopost_for_status_change(
                _seller(), _listing(publish_to_channel=True), ListingStatus.DRAFT
            )
            task.delay.assert_called_once()

    def test_skips_when_opted_out(self):
        with patch("app.workers.tasks.autopost.publish_listing_to_channel") as task:
            _dispatch_autopost_for_status_change(
                _seller(), _listing(publish_to_channel=False), ListingStatus.DRAFT
            )
            task.delay.assert_not_called()

    def test_missing_attr_defaults_to_publish(self):
        # Defensive getattr(..., True): an object without the attribute
        # (legacy / partially-hydrated) still publishes.
        listing = _listing()
        del listing.publish_to_channel
        with patch("app.workers.tasks.autopost.publish_listing_to_channel") as task:
            _dispatch_autopost_for_status_change(
                _seller(), listing, ListingStatus.DRAFT
            )
            task.delay.assert_called_once()

    def test_no_channel_never_publishes(self):
        with patch("app.workers.tasks.autopost.publish_listing_to_channel") as task:
            _dispatch_autopost_for_status_change(
                _seller(autopost_channel_id=None), _listing(), ListingStatus.DRAFT
            )
            task.delay.assert_not_called()


class TestOptOutLeavesOtherBranchesAlone:
    """The opt-out must NOT block sold / delete lifecycle syncing."""

    def test_mark_sold_ignores_opt_out(self):
        with patch("app.workers.tasks.autopost.mark_channel_post_sold") as task:
            _dispatch_autopost_for_status_change(
                _seller(),
                _listing(status=ListingStatus.SOLD, publish_to_channel=False),
                ListingStatus.ACTIVE,
            )
            task.delay.assert_called_once()

    def test_delete_ignores_opt_out(self):
        with patch("app.workers.tasks.autopost.delete_channel_post") as task:
            _dispatch_autopost_for_status_change(
                _seller(),
                _listing(status=ListingStatus.PAUSED, publish_to_channel=False),
                ListingStatus.ACTIVE,
            )
            task.delay.assert_called_once()
