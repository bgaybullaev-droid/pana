"""Block F F1 — listing-description prompt construction (point 2).

Covers the long-form "selling" prompt rewrite: the shared constant, the
expanded params block that now feeds the model every populated field, and
the worker prompt builder that substitutes localized params + scrubs PII.
"""

from types import SimpleNamespace

from app.core.prompts import LISTING_DESCRIPTION_PROMPT
from app.workers.tasks.ai_generation import _build_prompt, _params_block


def _rich_listing(**overrides):
    base = dict(
        id="00000000-0000-0000-0000-000000000000",
        property_type="apartment",
        type="sell",
        rooms=3,
        area=78.0,
        living_area=52.0,
        kitchen_area=12.0,
        land_area=None,
        floor=5,
        total_floors=9,
        ceiling_height=3.0,
        building_type="new",
        condition="euro",
        wall_material=None,
        district="yunusobod",
        region="toshkent_shahri",
        city=None,
        microdistrict=None,
        jk_name="Nest One",
        landmark=None,
        metro_station="Минг Урик",
        price=120000,
        currency="USD",
        price_per_sqm=None,
        rent_period=None,
        deposit=None,
        min_rent_months=None,
        is_negotiable=True,
        mortgage_ok=True,
        installment_ok=False,
        halol_ok=False,
        is_furnished=True,
        utilities_incl=False,
        allowed_pets=False,
        allowed_students=False,
        urgent_flag=False,
        amenities=None,
        nearby_amenities=None,
        raw_text="3-комн, евроремонт, телефон +998901234567",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_prompt_constant_shape():
    body = LISTING_DESCRIPTION_PROMPT
    assert "{params_block}" in body and "{raw_text}" in body
    # v3 — calm, short, paragraphed copy
    assert "MAXIMUM 500 characters" in body
    assert "2-3 short paragraphs" in body
    assert "NO exclamation marks" in body
    # price must NOT appear in the generated copy
    assert "Do NOT mention any price" in body
    # safety rails kept
    assert "never invent" in body
    assert "No phone numbers" in body
    # strict-JSON contract preserved
    assert '"ru"' in body and '"uz"' in body and '"uz_cyrl"' in body


def test_params_block_includes_rich_fields():
    block = _params_block(_rich_listing())
    assert "living_area_sqm: 52.0" in block
    assert "kitchen_area_sqm: 12.0" in block
    assert "ceiling_height_m: 3.0" in block
    assert 'building_type: ru="Новостройка"' in block
    assert 'condition: ru="Евроремонт"' in block
    assert "residential_complex: Nest One" in block
    assert "metro_station: Минг Урик" in block
    # boolean flags collapse into one features line (localized by the model)
    assert "features:" in block
    assert "mortgage available" in block
    assert "price negotiable" in block
    assert "furnished" in block


def test_params_block_omits_empty_fields():
    block = _params_block(_rich_listing(rooms=None, jk_name=None, mortgage_ok=False))
    assert "rooms:" not in block
    assert "residential_complex:" not in block
    assert "mortgage available" not in block


def test_params_block_omits_money_amounts():
    # v3 — price / price_per_sqm / deposit are shown separately on the page
    # and must NOT be fed to the model (no money amount in the generated copy).
    block = _params_block(
        _rich_listing(price=120000, price_per_sqm=1500, deposit=500)
    )
    assert "- price:" not in block
    assert "- price_per_sqm:" not in block
    assert "- deposit:" not in block
    assert "120000" not in block
    # qualitative deal flags stay (they are not money amounts)
    assert "price negotiable" in block


def test_build_prompt_substitutes_and_scrubs_pii():
    prompt = _build_prompt(_rich_listing())
    # placeholders substituted away
    assert "{params_block}" not in prompt and "{raw_text}" not in prompt
    # localized district present; lowercase raw key must not leak
    assert "Юнусабадский р-н" in prompt
    assert "yunusobod" not in prompt
    # PII scrubbed out of the raw_text section
    assert "+998901234567" not in prompt
    assert "[contact]" in prompt
