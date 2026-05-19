"""Block F V2.0 F3a — seo_meta service unit tests.

Pure-function tests: slug URL-safety, meta length caps,
hreflang completeness, JSON-LD `RealEstateListing` shape +
`None`-value stripping.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from types import SimpleNamespace
from typing import Optional
from uuid import uuid4

import pytest

from app.services.seo_meta import (
    SUPPORTED_LANGS,
    SEOMeta,
    build_filter_meta,
    build_listing_jsonld,
    build_listing_meta,
    slug_for_listing,
)

pytestmark = [pytest.mark.unit]


# ─────────────────────────────────────────────────────────────────────
# Listing stubs
# ─────────────────────────────────────────────────────────────────────


@dataclass
class _Img:
    original_url: str
    medium_url: Optional[str] = None
    large_url: Optional[str] = None
    is_primary: bool = False
    position: int = 0


def _listing(
    *,
    rooms: Optional[int] = 3,
    district: Optional[str] = "chilonzor",
    region: Optional[str] = "toshkent_shahri",
    area: Optional[float] = 65.0,
    price: int = 35000,
    currency: str = "USD",
    property_type: str = "apartment",
    type_: str = "sell",
    ai_ru: Optional[str] = "Просторная трёхкомнатная квартира в Чиланзаре с балконом и видом на парк.",
    ai_uz: Optional[str] = "Chilonzor tumanida 3-xonali keng kvartira, balkon va park manzarasi bilan.",
    ai_uz_cyrl: Optional[str] = "Чилонзор туманидаги уч хонали кенг квартира.",
    images: Optional[list[_Img]] = None,
    listing_id: Optional[object] = None,
    created_at: Optional[datetime] = None,
    updated_at: Optional[datetime] = None,
) -> SimpleNamespace:
    """Build a duck-typed Listing-like object the SEO functions accept."""
    return SimpleNamespace(
        id=listing_id or uuid4(),
        rooms=rooms,
        district=district,
        region=region,
        area=area,
        price=price,
        currency=currency,
        property_type=property_type,
        type=type_,
        title=None,
        ai_description_ru=ai_ru,
        ai_description_uz=ai_uz,
        ai_description_uz_cyrl=ai_uz_cyrl,
        description=None,
        images=(
            images
            if images is not None
            else [
                _Img(
                    original_url="https://cdn.example.com/o.jpg",
                    large_url="https://cdn.example.com/l.jpg",
                    medium_url="https://cdn.example.com/m.jpg",
                    is_primary=True,
                    position=0,
                )
            ]
        ),
        address=None,
        created_at=created_at or datetime(2026, 1, 1, 12, 0, 0),
        updated_at=updated_at or datetime(2026, 5, 1, 12, 0, 0),
    )


# ─────────────────────────────────────────────────────────────────────
# slug_for_listing
# ─────────────────────────────────────────────────────────────────────


class TestSlugForListing:
    _SAFE_RE = re.compile(r"^[a-z0-9-]+$")

    def test_basic_shape(self):
        l = _listing(rooms=3, district="chilonzor")
        assert slug_for_listing(l) == "3-rooms-chilonzor"

    def test_url_safe_chars_only(self):
        l = _listing(rooms=2, district="mirzo_ulugbek")
        s = slug_for_listing(l)
        assert self._SAFE_RE.match(s), f"unsafe chars in slug: {s!r}"

    def test_alias_normalisation(self):
        # Common cross-script variants resolve to the canonical Latin
        # key before slug composition — guarantees a single canonical
        # URL regardless of how the crawler captured the district.
        l = _listing(rooms=2, district="Chilanzar")
        assert slug_for_listing(l) == "2-rooms-chilonzor"
        l2 = _listing(rooms=2, district="сергелийский")
        assert slug_for_listing(l2) == "2-rooms-sergeli"

    def test_no_rooms_no_district_falls_back(self):
        l = _listing(rooms=None, district=None)
        assert slug_for_listing(l) == "listing"

    def test_only_district(self):
        l = _listing(rooms=None, district="sergeli")
        assert slug_for_listing(l) == "sergeli"

    def test_only_rooms(self):
        l = _listing(rooms=4, district=None)
        assert slug_for_listing(l) == "4-rooms"

    def test_max_length(self):
        l = _listing(rooms=99, district="mirzo_ulugbek")
        s = slug_for_listing(l)
        assert len(s) <= 30
        assert self._SAFE_RE.match(s)

    def test_deterministic(self):
        l = _listing(rooms=3, district="chilonzor")
        assert slug_for_listing(l) == slug_for_listing(l)

    def test_locale_independent(self):
        # Slug must be identical regardless of which locale rendered it
        # so the same /listing/<id>/<slug> resolves across all 3 langs.
        l = _listing(rooms=3, district="chilonzor")
        assert slug_for_listing(l, "ru") == slug_for_listing(l, "uz")
        assert slug_for_listing(l, "ru") == slug_for_listing(l, "uz-latn")


# ─────────────────────────────────────────────────────────────────────
# build_listing_meta
# ─────────────────────────────────────────────────────────────────────


class TestListingMeta:
    def test_title_under_60_chars(self):
        l = _listing()
        m = build_listing_meta(l, "ru")
        assert len(m.title) <= 60

    def test_description_under_160_chars(self):
        l = _listing(
            ai_ru="Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 10
        )
        m = build_listing_meta(l, "ru")
        assert len(m.description) <= 160

    def test_canonical_includes_lang_id_slug(self):
        lid = uuid4()
        l = _listing(listing_id=lid, rooms=3, district="chilonzor")
        m = build_listing_meta(l, "ru")
        assert f"/ru/listing/{lid}/3-rooms-chilonzor" in m.canonical

    def test_hreflang_contains_all_langs_plus_x_default(self):
        m = build_listing_meta(_listing(), "ru")
        assert set(m.hreflang.keys()) >= {"ru", "uz", "uz-latn", "x-default"}

    def test_og_image_from_primary_photo(self):
        l = _listing(
            images=[
                _Img(original_url="https://cdn/a.jpg", position=2, is_primary=False),
                _Img(original_url="https://cdn/b.jpg", large_url="https://cdn/b-l.jpg", position=0, is_primary=True),
            ]
        )
        m = build_listing_meta(l, "ru")
        assert m.og_image == "https://cdn/b-l.jpg"

    def test_no_image_returns_none(self):
        l = _listing(images=[])
        m = build_listing_meta(l, "ru")
        assert m.og_image is None

    def test_unsupported_lang_falls_back_to_ru(self):
        l = _listing()
        m = build_listing_meta(l, "fr")
        assert "/ru/listing/" in m.canonical

    @pytest.mark.parametrize("lang", list(SUPPORTED_LANGS))
    def test_meta_renders_for_each_lang(self, lang):
        l = _listing()
        m = build_listing_meta(l, lang)
        assert m.title
        assert m.description
        assert m.canonical.startswith("https://")

    def test_meta_description_falls_back_across_locales(self):
        # If the page's locale has no AI text but other locales do,
        # description should pull from the next available locale.
        l = _listing(ai_ru=None, ai_uz_cyrl=None, ai_uz="Latin Uzbek copy.")
        m = build_listing_meta(l, "ru")
        assert m.description  # non-empty


# ─────────────────────────────────────────────────────────────────────
# build_filter_meta
# ─────────────────────────────────────────────────────────────────────


class TestFilterMeta:
    def test_district_only_landing(self):
        m = build_filter_meta({"district": "chilonzor"}, "ru")
        assert m.canonical.endswith("/ru/tashkent/chilonzor")

    def test_deal_type_combo(self):
        m = build_filter_meta({"deal": "sell", "property_type": "apartment"}, "ru")
        assert m.canonical.endswith("/ru/sell/apartment")

    def test_three_param_combo(self):
        m = build_filter_meta(
            {"deal": "sell", "property_type": "apartment", "rooms": 3, "district": "chilonzor"},
            "ru",
        )
        assert m.canonical.endswith("/ru/sell/apartment/3-rooms/chilonzor")

    def test_title_under_60(self):
        m = build_filter_meta({"deal": "sell", "property_type": "apartment"}, "ru")
        assert len(m.title) <= 60

    def test_description_under_160(self):
        m = build_filter_meta(
            {"deal": "sell", "property_type": "apartment", "district": "chilonzor"},
            "ru",
        )
        assert len(m.description) <= 160

    def test_hreflang_covers_all_langs(self):
        m = build_filter_meta({"district": "chilonzor"}, "ru")
        assert {"ru", "uz", "uz-latn", "x-default"} <= set(m.hreflang.keys())


# ─────────────────────────────────────────────────────────────────────
# build_listing_jsonld
# ─────────────────────────────────────────────────────────────────────


class TestJsonLD:
    def test_realestatelisting_type(self):
        d = build_listing_jsonld(_listing(), "ru")
        assert d["@type"] == "RealEstateListing"
        assert d["@context"] == "https://schema.org"

    def test_required_fields_present(self):
        d = build_listing_jsonld(_listing(), "ru")
        for required in ("name", "description", "url", "image", "offers", "address"):
            assert required in d, f"missing {required}"

    def test_offers_has_price_and_currency(self):
        d = build_listing_jsonld(_listing(price=42000, currency="USD"), "ru")
        assert d["offers"]["price"] == 42000
        assert d["offers"]["priceCurrency"] == "USD"

    def test_null_fields_stripped(self):
        l = _listing(area=None, rooms=None, price=0, ai_ru=None, ai_uz=None, ai_uz_cyrl=None)
        d = build_listing_jsonld(l, "ru")
        assert "floorSize" not in d
        assert "numberOfRooms" not in d
        # offers is dropped when price is 0/missing
        assert "offers" not in d
        # Re-serialise to verify no naked `null` values in output.
        rendered = json.dumps(d, ensure_ascii=False)
        assert ": null" not in rendered

    def test_serialisable_to_json(self):
        d = build_listing_jsonld(_listing(), "ru")
        # If anything non-JSON-serialisable slipped through, this raises.
        json.dumps(d, ensure_ascii=False)

    def test_uses_locale_ai_text(self):
        l = _listing(
            ai_ru="Russian text.",
            ai_uz="Latin uzbek text.",
            ai_uz_cyrl="Кирилл матн.",
        )
        d_ru = build_listing_jsonld(l, "ru")
        d_uz_latn = build_listing_jsonld(l, "uz-latn")
        d_uz_cyrl = build_listing_jsonld(l, "uz")
        assert d_ru["description"].startswith("Russian")
        assert d_uz_latn["description"].startswith("Latin")
        assert d_uz_cyrl["description"].startswith("Кирилл")

    def test_floorsize_unitcode_is_mtk(self):
        d = build_listing_jsonld(_listing(area=78.5), "ru")
        assert d["floorSize"]["unitCode"] == "MTK"
        assert d["floorSize"]["value"] == 78.5

    def test_transaction_type_mapped(self):
        d_sell = build_listing_jsonld(_listing(type_="sell"), "ru")
        d_rent = build_listing_jsonld(_listing(type_="rent"), "ru")
        assert d_sell["transactionType"].endswith("Sale")
        assert d_rent["transactionType"].endswith("Rental")
