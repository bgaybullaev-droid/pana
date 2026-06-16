"""Block D V2.0 (D4) — autopost domain logic unit tests.

Pure-function coverage of :mod:`app.services.autopost`: the
state-transition matrix, the stale/media-cutoff predicates, the
connection-readiness gate, and the post renderer (truncation, footer,
SOLD overlay, primary-photo selection).

Note on the dispatch path
-------------------------
``autopost.decide_transition`` is the *spec* of what each listing-status
flip means, but it is **dead code** — no caller invokes it. The live
publish/sold/delete routing happens in
``app.api.v1.listings._dispatch_autopost_for_status_change``, which is
covered separately in ``tests/unit/test_autopost_dispatch_gate.py``
(including the per-listing ``publish_to_channel`` opt-out). We still
pin ``decide_transition`` here so the documented contract can't silently
rot, and so a future wiring of the domain function inherits a guard.

Listings/posts/sellers are built as lightweight ``SimpleNamespace``
duck types — the domain functions only read attributes, so we avoid a
DB round-trip entirely.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.bot.i18n import t
from app.db.models import ListingStatus, ListingType
from app.services import autopost

pytestmark = pytest.mark.unit


# =============================================================================
# decide_transition — the documented state matrix
# =============================================================================
class TestDecideTransition:
    S = ListingStatus

    @pytest.mark.parametrize(
        "old,new,has_post,expected",
        [
            # Creation / publish
            (None, S.ACTIVE, False, "publish"),
            (S.DRAFT, S.ACTIVE, False, "publish"),
            (S.ACTIVE, S.ACTIVE, True, "noop"),          # same status
            (S.DRAFT, S.ACTIVE, True, "noop"),           # already_posted
            # Sold
            (S.ACTIVE, S.SOLD, True, "mark_sold"),
            (S.ACTIVE, S.SOLD, False, "noop"),           # no post → nothing
            # Removal — any move into an inactive state with a live post
            (S.ACTIVE, S.PAUSED, True, "delete"),
            (S.ACTIVE, S.DELETED, True, "delete"),
            (S.ACTIVE, S.EXPIRED, True, "delete"),
            (S.PAUSED, S.DELETED, True, "delete"),
            # Removal target but no post → noop
            (S.ACTIVE, S.PAUSED, False, "noop"),
        ],
    )
    def test_matrix(self, old, new, has_post, expected):
        decision = autopost.decide_transition(
            old_status=old, new_status=new, has_existing_post=has_post
        )
        assert decision.action == expected


# =============================================================================
# is_post_stale — cabinet "stale" badge predicate
# =============================================================================
class TestIsPostStale:
    def test_stale_when_listing_version_advances(self):
        post = SimpleNamespace(last_listing_version=3)
        assert autopost.is_post_stale(post, SimpleNamespace(version=5)) is True

    def test_not_stale_when_versions_match(self):
        post = SimpleNamespace(last_listing_version=3)
        assert autopost.is_post_stale(post, SimpleNamespace(version=3)) is False

    def test_not_stale_when_post_ahead(self):
        post = SimpleNamespace(last_listing_version=7)
        assert autopost.is_post_stale(post, SimpleNamespace(version=5)) is False


# =============================================================================
# media_edit_allowed — Telegram 48h media-edit cutoff
# =============================================================================
class TestMediaEditAllowed:
    def test_allowed_within_window(self):
        post = SimpleNamespace(posted_at=datetime.utcnow() - timedelta(hours=10))
        assert autopost.media_edit_allowed(post) is True

    def test_blocked_after_window(self):
        post = SimpleNamespace(posted_at=datetime.utcnow() - timedelta(hours=49))
        assert autopost.media_edit_allowed(post) is False

    def test_boundary_is_exclusive(self):
        # Exactly at the 48h cutoff is NOT allowed (strict less-than).
        now = datetime(2026, 6, 1, 12, 0, 0)
        post = SimpleNamespace(posted_at=now - autopost.MEDIA_EDIT_CUTOFF)
        assert autopost.media_edit_allowed(post, now=now) is False

    def test_just_inside_boundary(self):
        now = datetime(2026, 6, 1, 12, 0, 0)
        post = SimpleNamespace(
            posted_at=now - autopost.MEDIA_EDIT_CUTOFF + timedelta(minutes=1)
        )
        assert autopost.media_edit_allowed(post, now=now) is True


# =============================================================================
# is_autopost_ready — channel-binding readiness gate
# =============================================================================
def _seller(**over):
    base = dict(
        autopost_enabled=True,
        autopost_channel_id=-1001234567890,
        autopost_verified_at=datetime.utcnow(),
    )
    base.update(over)
    return SimpleNamespace(**base)


class TestIsAutopostReady:
    def test_ready_when_all_set(self):
        assert autopost.is_autopost_ready(_seller()) is True

    def test_not_ready_without_verification(self):
        assert autopost.is_autopost_ready(_seller(autopost_verified_at=None)) is False

    def test_not_ready_when_disabled(self):
        assert autopost.is_autopost_ready(_seller(autopost_enabled=False)) is False

    def test_not_ready_without_channel(self):
        assert autopost.is_autopost_ready(_seller(autopost_channel_id=None)) is False


# =============================================================================
# render_post_body — caption rendering
# =============================================================================
def _listing(**over):
    base = dict(
        rooms=2,
        area=55.0,
        floor=3,
        total_floors=9,
        district="Chilonzor",
        price=50000,
        currency="USD",
        type=ListingType.SELL,
        ai_description_ru="Хорошая квартира",
        ai_description_uz="Yaxshi kvartira",
        ai_description_uz_cyrl="Яхши квартира",
        images=[],
        id="abc-123",
    )
    base.update(over)
    return SimpleNamespace(**base)


class TestRenderPostBody:
    @pytest.mark.parametrize("lang", ["ru", "uz", "uz_cyrl"])
    def test_footer_present_per_locale(self, lang):
        rendered = autopost.render_post_body(_listing(), lang)
        assert t(lang, "autopost_footer") in rendered.caption

    def test_button_url_is_listing_deeplink(self):
        rendered = autopost.render_post_body(_listing(id="xyz-999"), "ru")
        assert rendered.button_url.endswith("startapp=listing_xyz-999")
        assert rendered.button_label == t("ru", "btn_listing_details")

    def test_caption_truncated_to_telegram_limit(self):
        rendered = autopost.render_post_body(
            _listing(ai_description_ru="я" * 5000), "ru"
        )
        assert len(rendered.caption) <= 1024

    def test_ai_text_truncated_with_ellipsis(self):
        rendered = autopost.render_post_body(
            _listing(ai_description_ru="a" * 5000), "ru"
        )
        # _AI_TEXT_MAX caps the description body well under the caption limit.
        assert "…" in rendered.caption

    def test_sold_overlay_for_sell(self):
        rendered = autopost.render_post_body(
            _listing(type=ListingType.SELL), "ru", sold_overlay=True
        )
        assert rendered.caption.splitlines()[0] == t("ru", "autopost_overlay_sold")

    def test_sold_overlay_for_rent(self):
        rendered = autopost.render_post_body(
            _listing(type=ListingType.RENT), "ru", sold_overlay=True
        )
        assert rendered.caption.splitlines()[0] == t("ru", "autopost_overlay_rented")

    def test_no_overlay_by_default(self):
        rendered = autopost.render_post_body(_listing(), "ru")
        assert rendered.caption.splitlines()[0] != t("ru", "autopost_overlay_sold")

    def test_primary_photo_preferred_over_position(self):
        images = [
            SimpleNamespace(original_url="first.jpg", is_primary=False),
            SimpleNamespace(original_url="primary.jpg", is_primary=True),
        ]
        rendered = autopost.render_post_body(_listing(images=images), "ru")
        assert rendered.photo_url == "primary.jpg"

    def test_falls_back_to_first_image_without_primary(self):
        images = [
            SimpleNamespace(original_url="first.jpg", is_primary=False),
            SimpleNamespace(original_url="second.jpg", is_primary=False),
        ]
        rendered = autopost.render_post_body(_listing(images=images), "ru")
        assert rendered.photo_url == "first.jpg"

    def test_no_photo_when_no_images(self):
        rendered = autopost.render_post_body(_listing(images=[]), "ru")
        assert rendered.photo_url is None
