"""Codegen: backend listing-parameter i18n from the frontend locale files.

The frontend already carries the single source of truth for localized
display names of listing parameters (regions, districts, property types,
deal types, building types, repair conditions) under
``frontend/src/shared/i18n/locales/<locale>/{common,buyer}.json``.

The backend needs the SAME localized names when it builds AI-generation
prompts and the template fallback, so a buyer reading the Russian feed
sees "Алмазарский р-н" instead of the raw storage key "olmazor".

Rather than hand-duplicate ~190 districts × 3 locales (which silently
drifts), this script reads the frontend JSON and emits a self-contained
Python module ``app/core/listing_i18n.py``. Re-run it whenever the
frontend locale files change:

    python backend/scripts/gen_listing_i18n.py

Generation locales map to the three AI-output keys:
    ru       ← locales/ru        (Russian, Cyrillic)
    uz       ← locales/uz-latn   (Uzbek, Latin)
    uz_cyrl  ← locales/uz-cyrl   (Uzbek, Cyrillic)
"""

from __future__ import annotations

import json
import pathlib

# backend/scripts/gen_listing_i18n.py → repo root is two levels up.
ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCALES = ROOT / "frontend" / "src" / "shared" / "i18n" / "locales"
OUT = ROOT / "backend" / "app" / "core" / "listing_i18n.py"

# AI-output locale key → frontend locale directory.
LOCALE_DIRS = {"ru": "ru", "uz": "uz-latn", "uz_cyrl": "uz-cyrl"}


def _load(locale_dir: str, filename: str) -> dict:
    return json.loads((LOCALES / locale_dir / filename).read_text(encoding="utf-8"))


def _common(locale_dir: str) -> dict:
    return _load(locale_dir, "common.json")["locations"]


def _build_location_table(section: str) -> dict[str, dict[str, str]]:
    """section is 'region' or 'district'. Returns key → {lang: name}."""
    per_lang = {lang: _common(d)[section] for lang, d in LOCALE_DIRS.items()}
    keys = sorted(per_lang["ru"].keys())
    table: dict[str, dict[str, str]] = {}
    for key in keys:
        table[key] = {
            lang: per_lang[lang].get(key) or per_lang["ru"][key]
            for lang in LOCALE_DIRS
        }
    return table


def _build_flat_table(field_map: dict[str, str]) -> dict[str, dict[str, str]]:
    """field_map: storage_key → flat buyer.json dotted key."""
    per_lang = {lang: _load(d, "buyer.json") for lang, d in LOCALE_DIRS.items()}
    table: dict[str, dict[str, str]] = {}
    for storage_key, json_key in field_map.items():
        table[storage_key] = {
            lang: per_lang[lang].get(json_key) or per_lang["ru"].get(json_key) or storage_key
            for lang in LOCALE_DIRS
        }
    return table


def _fmt_table(name: str, table: dict[str, dict[str, str]]) -> str:
    lines = [f"{name}: dict[str, dict[str, str]] = {{"]
    for key, names in table.items():
        inner = ", ".join(f'"{lang}": {json.dumps(names[lang], ensure_ascii=False)}' for lang in LOCALE_DIRS)
        lines.append(f"    {json.dumps(key, ensure_ascii=False)}: {{{inner}}},")
    lines.append("}")
    return "\n".join(lines)


def main() -> None:
    region = _build_location_table("region")
    district = _build_location_table("district")
    property_type = _build_flat_table(
        {k: f"common.propertyType.{k}" for k in ("apartment", "house", "commercial", "land")}
    )
    deal_type = _build_flat_table({"sell": "listing.typeSell", "rent": "listing.typeRent"})
    building_type = _build_flat_table(
        {k: f"listing.buildingType.{k}" for k in ("new", "secondary")}
    )
    condition = _build_flat_table(
        {k: f"listing.condition.{k}" for k in ("euro", "cosmetic", "needs_repair", "rough")}
    )

    header = '''"""Localized display names for listing parameters (AUTO-GENERATED).

DO NOT EDIT BY HAND. Regenerate with:
    python backend/scripts/gen_listing_i18n.py

Source of truth: frontend/src/shared/i18n/locales/{ru,uz-latn,uz-cyrl}/
{common,buyer}.json. This mirror lets backend-side text generation (AI
prompts + template fallback) emit the correct language/script per locale
instead of the raw storage keys (e.g. "olmazor" → "Алмазарский р-н").

Locale keys match the three AI-output locales: ru, uz (Latin), uz_cyrl.
"""

from __future__ import annotations

from typing import Optional

LOCALES = ("ru", "uz", "uz_cyrl")
'''

    helpers = '''

def _lookup(table: dict[str, dict[str, str]], key: Optional[str], lang: str) -> str:
    """Localized name for a storage key; falls back to the raw key.

    Unknown keys (e.g. legacy crawler values not in the registry) return
    the key verbatim so we never crash a generation on a missing entry.
    """
    if not key:
        return ""
    entry = table.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get("ru") or key


def localize_region(key: Optional[str], lang: str) -> str:
    return _lookup(REGION_NAMES, key, lang)


def localize_district(key: Optional[str], lang: str) -> str:
    return _lookup(DISTRICT_NAMES, key, lang)


def localize_property_type(key: Optional[str], lang: str) -> str:
    return _lookup(PROPERTY_TYPE_NAMES, key, lang)


def localize_deal_type(key: Optional[str], lang: str) -> str:
    return _lookup(DEAL_TYPE_NAMES, key, lang)


def localize_building_type(key: Optional[str], lang: str) -> str:
    return _lookup(BUILDING_TYPE_NAMES, key, lang)


def localize_condition(key: Optional[str], lang: str) -> str:
    return _lookup(CONDITION_NAMES, key, lang)
'''

    body = "\n\n".join(
        [
            _fmt_table("REGION_NAMES", region),
            _fmt_table("DISTRICT_NAMES", district),
            _fmt_table("PROPERTY_TYPE_NAMES", property_type),
            _fmt_table("DEAL_TYPE_NAMES", deal_type),
            _fmt_table("BUILDING_TYPE_NAMES", building_type),
            _fmt_table("CONDITION_NAMES", condition),
        ]
    )

    OUT.write_text(header + "\n" + body + "\n" + helpers, encoding="utf-8")
    print(
        f"Wrote {OUT.relative_to(ROOT)}: "
        f"{len(region)} regions, {len(district)} districts, "
        f"{len(property_type)} property types, {len(deal_type)} deal types, "
        f"{len(building_type)} building types, {len(condition)} conditions."
    )


if __name__ == "__main__":
    main()
