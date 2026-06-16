"""Block D V2.0 (D5) — golden corpus for the bot query parser.

Table-driven regression suite for :func:`app.services.query_parser.parse`.
Every expectation here was captured from the live parser, so the suite
locks current behaviour and screams on any drift — district aliasing,
room word-forms, the magnitude/currency rules, and the deal/property
dictionaries.

The corpus is a *living asset*: when FU5 telemetry surfaces real
unrecognised queries, add them here (with the desired outcome) before
touching the dictionaries, so the fix ships with its regression guard.

Currency / magnitude rules worth remembering (they trip people up):

* ``price_currency`` is only set when a price bound actually survives.
* UZS is the default; an explicit USD token (``у.е.``, ``$``, ``usd``,
  ``доллар`` …) anywhere flips the whole query to USD.
* A magnitude-less UZS bound below 1 000 000 is dropped as implausible
  (``"до 35тыс"`` with no currency → no price), because applying it
  would zero out every result. The same bound with a USD token stays.
* Only ``тыс/k/к/млн/mln/m`` are magnitudes — ``млрд`` is NOT, so
  ``"до 1 млрд"`` extracts no price.
"""

import pytest

from app.services.query_parser import parse

pytestmark = pytest.mark.unit


# ─────────────────────────────────────────────────────────────────────
# Districts — Cyrillic bare forms, Latin spellings, typos, suffixed,
# and a few non-Tashkent cities used as districts. Canonical key wins.
# ─────────────────────────────────────────────────────────────────────
DISTRICT_CASES = [
    ("Чиланзар", "chilonzor"),
    ("чиланзар", "chilonzor"),
    ("Chilanzar", "chilonzor"),
    ("chilanzar", "chilonzor"),
    ("chilonzor", "chilonzor"),
    ("Юнусабад", "yunusobod"),
    ("yunusobod", "yunusobod"),
    ("yunusabad", "yunusobod"),
    ("Мирзо-Улугбек", "mirzo_ulugbek"),
    ("mirzo ulugbek", "mirzo_ulugbek"),
    ("mirzo_ulugbek", "mirzo_ulugbek"),
    ("Сергели", "sergeli"),
    ("sergeli", "sergeli"),
    ("sergili", "sergeli"),
    ("Мирабад", "mirobod"),
    ("mirobod", "mirobod"),
    ("mirabad", "mirobod"),
    ("Алмазар", "olmazor"),
    ("olmazor", "olmazor"),
    ("Учтепа", "uchtepa"),
    ("uchtepa", "uchtepa"),
    ("Яккасарай", "yakkasaroy"),
    ("yakkasaroy", "yakkasaroy"),
    ("Бектемир", "bektemir"),
    ("bektemir", "bektemir"),
    ("Яшнабад", "yashnobod"),
    ("yashnobod", "yashnobod"),
    ("samarkand", "samarqand_sh"),
    ("fergana", "fargona_sh"),
    ("andijan", "andijon_sh"),
    ("bukhara", "buxoro_sh"),
]


class TestDistricts:
    @pytest.mark.parametrize("text,expected", DISTRICT_CASES)
    def test_district_canonical_key(self, text, expected):
        p = parse(text)
        assert p.district == expected
        assert "district" in p.extracted_fields
        assert p.is_empty is False


# ─────────────────────────────────────────────────────────────────────
# Rooms — Russian/Uzbek digit forms and spelled-out word forms.
# MVP semantics: rooms_min == rooms_max == n.
# ─────────────────────────────────────────────────────────────────────
ROOM_CASES = [
    ("1комн", 1),
    ("2комн", 2),
    ("2-комн", 2),
    ("3 комнаты", 3),
    ("4-комн", 4),
    ("1-комн", 1),
    ("однокомнатная", 1),
    ("двухкомнатная", 2),
    ("трёхкомнатная", 3),
    ("четырёхкомнатная", 4),
    ("пятикомнатная", 5),
    ("1 xona", 1),
    ("2 xona", 2),
    ("3-xonali", 3),
    ("4 xonali", 4),
    ("bir xonali", 1),
    ("ikki xonali", 2),
    ("uch xonali", 3),
    ("besh xonali", 5),
]


class TestRooms:
    @pytest.mark.parametrize("text,n", ROOM_CASES)
    def test_room_count(self, text, n):
        p = parse(text)
        assert p.rooms_min == n
        assert p.rooms_max == n
        assert "rooms" in p.extracted_fields


# ─────────────────────────────────────────────────────────────────────
# Prices — (text) → (price_min, price_max, price_currency).
# Covers USD detection, magnitude multipliers, ranges, and the
# implausible-UZS-bound drop.
# ─────────────────────────────────────────────────────────────────────
PRICE_CASES = [
    # USD via token — bound is kept even when small.
    ("до 35тыс у.е.", None, 35000, "USD"),
    ("до $40k", None, 40000, "USD"),
    ("от 50 тыс у.е.", 50000, None, "USD"),
    ("до 100000 у.е.", None, 100000, "USD"),
    ("от 30000 до 80000 у.е.", 30000, 80000, "USD"),
    ("от 5000 usd", 5000, None, "USD"),
    ("до 500 долларов", None, 500, "USD"),
    # UZS magnitudes that survive the plausibility floor.
    ("200 млн", None, 200000000, "UZS"),
    ("от 100 млн", 100000000, None, "UZS"),
    ("200 млн so'm", None, 200000000, "UZS"),
    # Dropped: magnitude-less / sub-million UZS / unsupported "млрд".
    ("до 1 млрд", None, None, None),
    ("до 35тыс", None, None, None),
    ("до 300", None, None, None),
    ("до 35000 сум", None, None, None),
]


class TestPrices:
    @pytest.mark.parametrize("text,exp_min,exp_max,exp_cur", PRICE_CASES)
    def test_price_bounds_and_currency(self, text, exp_min, exp_max, exp_cur):
        p = parse(text)
        assert p.price_min == exp_min
        assert p.price_max == exp_max
        assert p.price_currency == exp_cur

    def test_price_currency_only_set_with_a_bound(self):
        # A bare USD token without any number must NOT invent a currency.
        p = parse("квартира у.е.")
        assert p.price_min is None and p.price_max is None
        assert p.price_currency is None


# ─────────────────────────────────────────────────────────────────────
# Deal type — sell / rent vocabulary (RU + UZ).
# ─────────────────────────────────────────────────────────────────────
DEAL_CASES = [
    ("продажа", "sell"),
    ("купить", "sell"),
    ("куплю", "sell"),
    ("sotiladi", "sell"),
    ("sotuv", "sell"),
    ("аренда", "rent"),
    ("снять", "rent"),
    ("сниму", "rent"),
    ("ijara", "rent"),
    ("ijaraga", "rent"),
    ("kira", "rent"),
]


class TestDealType:
    @pytest.mark.parametrize("text,expected", DEAL_CASES)
    def test_deal_type(self, text, expected):
        p = parse(text)
        assert p.deal_type == expected
        assert "deal_type" in p.extracted_fields


# ─────────────────────────────────────────────────────────────────────
# Property type — apartment / house / commercial / land (RU + UZ).
# ─────────────────────────────────────────────────────────────────────
PROPERTY_CASES = [
    ("квартира", "apartment"),
    ("квартиру", "apartment"),
    ("kvartira", "apartment"),
    ("xonadon", "apartment"),
    ("дом", "house"),
    ("uy", "house"),
    ("hovli", "house"),
    ("офис", "commercial"),
    ("коммерческая", "commercial"),
    ("ofis", "commercial"),
    ("участок", "land"),
    ("yer", "land"),
]


class TestPropertyType:
    @pytest.mark.parametrize("text,expected", PROPERTY_CASES)
    def test_property_type(self, text, expected):
        p = parse(text)
        assert p.property_type == expected
        assert "property_type" in p.extracted_fields


# ─────────────────────────────────────────────────────────────────────
# Negatives — casual chat / empty input extracts nothing → is_empty.
# ─────────────────────────────────────────────────────────────────────
EMPTY_CASES = ["привет", "ужин", "как дела", "спасибо", "", ".", "просто текст"]


class TestEmpty:
    @pytest.mark.parametrize("text", EMPTY_CASES)
    def test_unparseable_is_empty(self, text):
        p = parse(text)
        assert p.is_empty is True
        assert p.extracted_fields == ()
        assert p.district is None
        assert p.rooms_min is None
        assert p.price_min is None and p.price_max is None
        assert p.deal_type is None
        assert p.property_type is None


# ─────────────────────────────────────────────────────────────────────
# Combined queries — the realistic "all-at-once" inputs.
# ─────────────────────────────────────────────────────────────────────
class TestCombined:
    def test_ru_full_query(self):
        p = parse("2-комн Чиланзар до 35тыс у.е. продажа")
        assert p.district == "chilonzor"
        assert p.rooms_min == 2 and p.rooms_max == 2
        assert p.price_max == 35000 and p.price_currency == "USD"
        assert p.deal_type == "sell"
        assert set(p.extracted_fields) == {"district", "rooms", "deal_type", "price"}
        assert p.is_empty is False

    def test_uz_full_query(self):
        p = parse("3 xonali kvartira Yunusobod ijara")
        assert p.district == "yunusobod"
        assert p.rooms_min == 3
        assert p.deal_type == "rent"
        assert p.property_type == "apartment"
        assert p.is_empty is False

    def test_room_digit_not_parsed_as_price(self):
        # "2-комн" must not leak its "2" into the price bound.
        p = parse("2-комн")
        assert p.rooms_min == 2
        assert p.price_min is None and p.price_max is None

    def test_raw_text_preserved(self):
        assert parse("  Чиланзар  ").raw_text == "Чиланзар"
