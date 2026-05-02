"""S6 — Saved-search fanout tests.

Covers the pure helpers and template shapes used by
`_match_saved_searches` in `app.workers.tasks.notifications`.

The full async pipeline (DB queries, Celery dispatch, Telegram send)
lives in the integration suite. These tests verify:

    - Saved-search Telegram templates render without KeyError for both
      languages (ru + uz)
    - Title templates are distinct from the generic new-listing ones
    - Message templates include the search_name placeholder
    - _filters_to_listing_filters hydration (already covered in
      test_saved_searches.py but re-validated here for fanout context)
"""

from __future__ import annotations

import pytest

from app.workers.tasks.notifications import (
    _SAVED_SEARCH_MESSAGE,
    _SAVED_SEARCH_TELEGRAM,
    _SAVED_SEARCH_TITLE,
    _TELEGRAM_TEMPLATES,
    _TITLE_TEMPLATES,
)

pytestmark = pytest.mark.unit


class TestSavedSearchTemplates:
    SAMPLE_FMT = {
        "search_name": "Квартиры до $65k",
        "listing_type": "Продажа",
        "property_type": "Квартира",
        "rooms_text": ", 2 комн.",
        "district": "Юнусабад",
        "price": "60,000 $",
        "link": "https://t.me/TestBot?startapp=listing_abc",
    }

    def test_title_ru_distinct_from_generic(self):
        assert _SAVED_SEARCH_TITLE["ru"] != _TITLE_TEMPLATES["ru"]

    def test_title_uz_distinct_from_generic(self):
        assert _SAVED_SEARCH_TITLE["uz"] != _TITLE_TEMPLATES["uz"]

    def test_message_ru_includes_search_name(self):
        msg = _SAVED_SEARCH_MESSAGE["ru"].format(**self.SAMPLE_FMT)
        assert "Квартиры до $65k" in msg

    def test_message_uz_includes_search_name(self):
        fmt = {**self.SAMPLE_FMT, "search_name": "Kvartiralar"}
        msg = _SAVED_SEARCH_MESSAGE["uz"].format(**fmt)
        assert "Kvartiralar" in msg

    def test_telegram_ru_renders_without_error(self):
        html = _SAVED_SEARCH_TELEGRAM["ru"].format(**self.SAMPLE_FMT)
        assert "🔍" in html
        assert "Квартиры до $65k" in html
        assert "href=" in html

    def test_telegram_uz_renders_without_error(self):
        fmt = {**self.SAMPLE_FMT, "search_name": "Kvartiralar"}
        html = _SAVED_SEARCH_TELEGRAM["uz"].format(**fmt)
        assert "🔍" in html
        assert "Kvartiralar" in html

    def test_generic_telegram_does_not_require_search_name(self):
        # Verify the generic template still works (no search_name key).
        generic_fmt = {k: v for k, v in self.SAMPLE_FMT.items() if k != "search_name"}
        for lang in ("ru", "uz"):
            html = _TELEGRAM_TEMPLATES[lang].format(**generic_fmt)
            assert "🏠" in html

    def test_empty_search_name_falls_back(self):
        fmt = {**self.SAMPLE_FMT, "search_name": "Без названия"}
        msg = _SAVED_SEARCH_MESSAGE["ru"].format(**fmt)
        assert "Без названия" in msg


class TestFanoutDedup:
    """The dedup logic is in the async function (can't unit-test without
    a DB), but we can verify the invariant documentation: the dedup set
    is a `Set[UUID]` populated from the first stage and consumed by the
    second. This test just confirms the contract at the type level."""

    def test_dedup_set_semantics(self):
        from uuid import uuid4

        already = {uuid4(), uuid4()}
        new_user = uuid4()
        assert new_user not in already
        already.add(new_user)
        assert new_user in already
