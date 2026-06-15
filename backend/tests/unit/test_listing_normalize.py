"""BACKLOG #4 — unit tests for the shared listing normalization layer.

Covers the human title generator (ru / uz / uz_cyrl) and the canonical
builders (field mapping + generated title) used by the app feed/detail and
the bot. Pure functions only — no DB; rows are lightweight stubs.
"""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import listing_normalize as N

pytestmark = pytest.mark.unit


def _val(v):
    """Mimic a SQLAlchemy enum member exposing ``.value``."""
    return SimpleNamespace(value=v)


# ── generate_title ───────────────────────────────────────────────────


def test_title_apartment_rooms_district_ru():
    assert (
        N.generate_title(
            property_type="apartment", rooms=2, district="chilonzor", lang="ru"
        )
        == "2-комн. квартира, Чиланзарский р-н"
    )


def test_title_apartment_rooms_district_uz():
    assert (
        N.generate_title(
            property_type="apartment", rooms=2, district="chilonzor", lang="uz"
        )
        == "2 xonali kvartira, Chilonzor t."
    )


def test_title_apartment_uz_cyrl_script():
    title = N.generate_title(
        property_type="apartment", rooms=2, district="chilonzor", lang="uz_cyrl"
    )
    assert title.startswith("2 хонали ")  # Cyrillic rooms suffix
    assert title.endswith("Чилонзор т.")  # Cyrillic district label


def test_title_no_rooms_keeps_type_capitalized():
    # Without a room count the property type leads the title → stays capitalized.
    assert (
        N.generate_title(
            property_type="apartment", rooms=None, district="chilonzor", lang="ru"
        )
        == "Квартира, Чиланзарский р-н"
    )


def test_title_no_district_omitted():
    assert (
        N.generate_title(property_type="apartment", rooms=2, district=None, lang="ru")
        == "2-комн. квартира"
    )


def test_title_house_rooms_gender_safe():
    # Abbreviated "-комн." avoids the ungrammatical "3-комнатная дом".
    assert (
        N.generate_title(property_type="house", rooms=3, district="chilonzor", lang="ru")
        == "3-комн. дом, Чиланзарский р-н"
    )


def test_title_unknown_district_falls_back_to_raw():
    title = N.generate_title(
        property_type="apartment", rooms=1, district="Неизвестный массив", lang="ru"
    )
    assert title == "1-комн. квартира, Неизвестный массив"


def test_title_crawled_raw_district_gets_localized():
    # A crawled free-form spelling is canonicalized then localized.
    assert (
        N.generate_title(
            property_type="apartment", rooms=2, district="Чиланзар", lang="ru"
        )
        == "2-комн. квартира, Чиланзарский р-н"
    )


# ── crawled builders ─────────────────────────────────────────────────


def _tg(**overrides):
    base = dict(
        id=uuid4(),
        property_type="office",
        listing_type="sale",
        price=50000.0,
        currency="usd",
        rooms=2,
        area_sqm=55.0,
        floor=3,
        total_floors=9,
        region="toshkent_shahri",
        district="chilonzor",
        address=None,
        description="Просторный офис",
        raw_text="raw",
        images=["http://x/1.jpg", "http://x/2.jpg"],
        contact_phone="+998901112233",
        created_at=datetime(2026, 1, 1),
        amenities=None,
        confidence=0.9,
        source_channel="@chan",
        building_type=None,
        condition=None,
        land_purpose=None,
        original_language="ru",
        translation_status="pending",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_telegram_to_canonical_maps_and_normalizes():
    c = N.telegram_to_canonical(_tg(), lang="ru")
    assert c.source == "telegram"
    assert c.type == "sell"  # "sale" → "sell"
    assert c.property_type == "commercial"  # "office" → "commercial"
    assert c.currency == "USD"  # upper-cased
    assert c.area == 55.0  # area_sqm → area
    assert c.images[0].url == "http://x/1.jpg"
    # Title generated from the normalized property type + rooms + district.
    assert c.title == "2-комн. коммерция, Чиланзарский р-н"


def _olx(**overrides):
    base = _tg(
        id=uuid4(),
        property_type="apartment",
        listing_type="rent",
        currency="UZS",
        url="https://olx.uz/x",
        seller_name="Иван",
        views_count=12,
    ).__dict__.copy()
    base.pop("source_channel", None)
    base.update(overrides)
    return SimpleNamespace(**base)


def test_olx_to_canonical_maps_fields():
    c = N.olx_to_canonical(_olx(), lang="uz")
    assert c.source == "olx"
    assert c.type == "rent"
    assert c.property_type == "apartment"
    assert c.currency == "UZS"
    assert c.source_url == "https://olx.uz/x"
    assert c.seller_name == "Иван"
    assert c.title == "2 xonali kvartira, Chilonzor t."


# ── native builder (title fallback) ──────────────────────────────────


def _native(**overrides):
    fields = (
        "rooms area floor total_floors region district latitude longitude phone "
        "views_count favorites_count comments_count is_boosted is_highlighted "
        "seller_id seller seller_type seller_telegram amenities building_type "
        "condition land_purpose market_type wall_material listing_subtype balcony "
        "house_type house_condition location_type living_area kitchen_area land_area "
        "furniture is_furnished garage basement buildings_exist fence land_shape "
        "ceiling_height water_supply electricity heating gas_supply sewage "
        "commercial_type price_per_sqm entrance parking_comm building_class "
        "is_negotiable deed_type urgent_flag rent_period deposit utilities_incl "
        "min_rent_months allowed_students allowed_pets rent_payment mortgage_ok "
        "installment_ok halol_ok city microdistrict jk_name landmark metro_station "
        "nearby_amenities original_language"
    ).split()
    base = {f: None for f in fields}
    base.update(
        id=uuid4(),
        type=_val("sell"),
        property_type=_val("apartment"),
        currency=_val("USD"),
        price=80000.0,
        rooms=2,
        district="chilonzor",
        images=None,
        title="Уютная квартира в центре",
        created_at=datetime(2026, 1, 1),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_native_to_canonical_uses_db_title():
    c = N.native_to_canonical(_native(), lang="ru")
    assert c.source == "main"
    assert c.title == "Уютная квартира в центре"


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_native_to_canonical_generates_title_when_blank(blank):
    c = N.native_to_canonical(_native(title=blank), lang="ru")
    assert c.title == "2-комн. квартира, Чиланзарский р-н"


# ── photo helpers ────────────────────────────────────────────────────


def test_crawled_photo_url_first_string():
    assert N.crawled_photo_url(["http://a/1.jpg", "http://a/2.jpg"]) == "http://a/1.jpg"
    assert N.crawled_photo_url(None) is None
    assert N.crawled_photo_url([]) is None


def test_native_primary_photo_prefers_primary_then_lighter():
    imgs = [
        SimpleNamespace(is_primary=False, medium_url="m0", large_url="l0", original_url="o0"),
        SimpleNamespace(is_primary=True, medium_url="m1", large_url="l1", original_url="o1"),
    ]
    assert N.native_primary_photo(SimpleNamespace(images=imgs)) == "m1"
    # No medium → fall back to large.
    imgs2 = [SimpleNamespace(is_primary=True, medium_url=None, large_url="l", original_url="o")]
    assert N.native_primary_photo(SimpleNamespace(images=imgs2)) == "l"
    assert N.native_primary_photo(SimpleNamespace(images=None)) is None
