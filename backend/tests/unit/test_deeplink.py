"""Block D V2.0 (D3) — deep-link builder unit tests.

Pure (no-DB) coverage of the synchronous deep-link surface:
``build_listing_link``, ``build_found_link``, and the ``generate_short_id``
primitive (length + URL/human-safe alphabet). The async, DB-backed
builders/resolvers (``build_filter_link`` → ``GET /deep-links/{id}``)
are exercised in ``tests/integration/api/test_deep_links_routes.py``.
"""

from uuid import uuid4

import pytest

from app.services import deeplink

pytestmark = pytest.mark.unit


class TestBuildListingLink:
    def test_format(self):
        uid = uuid4()
        url = deeplink.build_listing_link(uid)
        assert url == f"https://t.me/{deeplink._bot_username()}?startapp=listing_{uid}"

    def test_startapp_scheme(self):
        url = deeplink.build_listing_link(uuid4())
        assert url.startswith("https://t.me/")
        assert "?startapp=listing_" in url

    def test_accepts_str_id(self):
        url = deeplink.build_listing_link("abc-123")
        assert url.endswith("?startapp=listing_abc-123")

    def test_payload_within_telegram_limit(self):
        # The opaque ``listing_<uuid>`` payload must stay under Telegram's
        # 64-char start_param cap (asserted inside the builder too).
        uid = uuid4()
        assert len(f"listing_{uid}") <= 64


class TestBuildFoundLink:
    def test_bare_found_token(self):
        url = deeplink.build_found_link()
        assert url.endswith("?startapp=found")


class TestGenerateShortId:
    def test_default_length(self):
        assert len(deeplink.generate_short_id()) == deeplink._SHORT_ID_LENGTH == 12

    def test_custom_length(self):
        assert len(deeplink.generate_short_id(8)) == 8

    def test_alphabet_is_url_and_human_safe(self):
        # Crockford base32 minus I, L, O, U — no ambiguous glyphs.
        for ch in "ILOU":
            assert ch not in deeplink._ALPHABET
        sid = deeplink.generate_short_id(64)
        assert set(sid).issubset(set(deeplink._ALPHABET))

    def test_ids_are_unique_in_practice(self):
        ids = {deeplink.generate_short_id() for _ in range(2000)}
        # ~60 bits of entropy → no collisions across a few thousand draws.
        assert len(ids) == 2000
