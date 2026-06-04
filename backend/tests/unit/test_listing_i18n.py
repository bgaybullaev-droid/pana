"""Block F F1 — listing-parameter localization regression tests.

Guards the fix for the bug where the Russian listing copy showed the raw
Latin district key ("olmazor") instead of "Алмазарский р-н", because the
backend fed raw storage keys into the AI prompt and template fallback.
"""

from types import SimpleNamespace

import pytest

from app.core import listing_i18n as L
from app.core.regions import ALL_DISTRICTS, REGIONS
from app.workers.tasks.ai_generation import _params_block, _template_fallback


# ── localization mirror ──────────────────────────────────────────────


def test_district_localized_per_locale():
    assert L.localize_district("olmazor", "ru") == "Алмазарский р-н"
    assert L.localize_district("olmazor", "uz") == "Olmazor t."
    assert L.localize_district("olmazor", "uz_cyrl") == "Олмазор т."


def test_region_and_enums_localized():
    assert L.localize_region("toshkent_shahri", "ru") == "Ташкент"
    assert L.localize_property_type("apartment", "ru") == "Квартира"
    assert L.localize_property_type("apartment", "uz") == "Kvartira"
    assert L.localize_deal_type("sell", "ru") == "Продажа"


def test_unknown_key_falls_back_to_raw_key():
    # Legacy crawler values not in the registry must not crash generation.
    assert L.localize_district("some_legacy_value", "ru") == "some_legacy_value"
    assert L.localize_district(None, "ru") == ""


def test_every_registry_district_has_three_locales():
    """The i18n mirror must cover every canonical district key."""
    for key in ALL_DISTRICTS:
        entry = L.DISTRICT_NAMES.get(key)
        assert entry is not None, f"missing district translation: {key}"
        for lang in ("ru", "uz", "uz_cyrl"):
            assert entry.get(lang), f"{key} missing {lang}"


def test_yangihayot_synced_into_registry():
    """Regression: yangihayot was missing from the backend registry."""
    assert "yangihayot" in REGIONS["toshkent_shahri"]
    assert L.localize_district("yangihayot", "ru") == "Янгихаётский р-н"


# ── generation wiring ────────────────────────────────────────────────


def _listing(**overrides):
    base = dict(
        rooms=1,
        property_type="apartment",
        type="sell",
        district="olmazor",
        region="toshkent_shahri",
        area=40.0,
        floor=3,
        total_floors=5,
        price=80000,
        currency="USD",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_template_fallback_uses_cyrillic_district():
    text = _template_fallback(_listing(), "ru")
    assert "olmazor" not in text
    assert "Алмазарский р-н" in text
    assert text == "1-комн. квартира, Алмазарский р-н, 40 м²"


@pytest.mark.parametrize(
    "lang,needle",
    [("uz", "Olmazor t."), ("uz_cyrl", "Олмазор т.")],
)
def test_template_fallback_uzbek_scripts(lang, needle):
    assert needle in _template_fallback(_listing(), lang)


def test_params_block_feeds_localized_names():
    block = _params_block(_listing())
    # Raw key must not leak; all three localized district names present.
    assert 'district: ru="Алмазарский р-н"' in block
    assert 'uz="Olmazor t."' in block
    assert 'uz_cyrl="Олмазор т."' in block
    assert 'property_type: ru="Квартира"' in block
    # price keeps the plain currency code, not the enum repr.
    assert "price: 80000 USD" in block
