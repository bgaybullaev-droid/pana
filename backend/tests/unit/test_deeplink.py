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


class TestParseFilterSlug:
    """FU6 — decode human marketing slugs into filter payloads.

    Grammar: ``<district>[_<N>rooms][_buy|_sale|_sell|_rent]``. The
    district head is mandatory and resolved through the shared alias
    tables; rooms/deal tokens are optional and order-independent.
    """

    def test_full_slug(self):
        assert deeplink.parse_filter_slug("chilonzor_2rooms_rent") == {
            "district": "chilonzor",
            "rooms_min": 2,
            "rooms_max": 2,
            "deal_type": "rent",
        }

    def test_bare_district(self):
        assert deeplink.parse_filter_slug("yunusobod") == {"district": "yunusobod"}

    def test_alias_district_folds_to_canonical_key(self):
        # Latin / typo spellings collapse to the canonical key.
        assert deeplink.parse_filter_slug("chilanzar_rent") == {
            "district": "chilonzor",
            "deal_type": "rent",
        }

    def test_multiword_district_key(self):
        # District keys that themselves contain underscores survive the
        # tail-peeling (rooms/deal are stripped first, the rest re-joined).
        assert deeplink.parse_filter_slug("mirzo_ulugbek_3rooms") == {
            "district": "mirzo_ulugbek",
            "rooms_min": 3,
            "rooms_max": 3,
        }

    def test_buy_and_sale_synonyms_fold_to_sell(self):
        assert deeplink.parse_filter_slug("sergeli_buy")["deal_type"] == "sell"
        assert deeplink.parse_filter_slug("sergeli_sale")["deal_type"] == "sell"

    def test_tail_order_is_independent(self):
        # Defensive: deal-before-rooms still decodes the same.
        assert deeplink.parse_filter_slug("chilonzor_rent_2rooms") == {
            "district": "chilonzor",
            "rooms_min": 2,
            "rooms_max": 2,
            "deal_type": "rent",
        }

    def test_rooms_only_is_rejected(self):
        # No district head → not a valid filter slug.
        assert deeplink.parse_filter_slug("2rooms_rent") is None

    def test_garbage_is_rejected(self):
        assert deeplink.parse_filter_slug("qwerty_zzz") is None

    def test_empty_is_none(self):
        assert deeplink.parse_filter_slug("") is None


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
