"""Block D — translation key-set parity guard.

A drift guard for the two i18n surfaces Block D touches:

* **Bot** (``app/bot/translations/{ru,uz,uz_cyrl}.json``) — flat
  ``snake_case`` keys; every locale must carry the same set so a
  ``t(lang, key)`` lookup never silently falls back to Russian.
* **Frontend seller namespace**
  (``frontend/src/shared/i18n/locales/{ru,uz,uz-cyrl,uz-latn}/seller.json``)
  — mostly flat dotted keys with one nested ``autopost`` object; all
  four locales must agree on the (plural-normalised) key set.

i18next plural variants (``key_one`` / ``key_few`` / ``key_many`` …) are
collapsed to their base before comparison, because CLDR plural
categories legitimately differ across languages (Russian has
few/many; Uzbek does not). We compare *base* keys, not raw leaves.

Pure pytest reading JSON straight from the repo — no FE tooling, no
running app — so it stays green in the backend test job and screams the
moment a new key lands in one locale but not its siblings (the guard
FU7's new keys will lean on).
"""

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# backend/tests/unit/this_file → parents[3] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BOT_DIR = _REPO_ROOT / "backend" / "app" / "bot" / "translations"
_FE_LOCALES = _REPO_ROOT / "frontend" / "src" / "shared" / "i18n" / "locales"

_PLURAL_SUFFIX = re.compile(r"_(?:zero|one|two|few|many|other)$")


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _flatten(obj: dict, prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in obj.items():
        full = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys |= _flatten(value, full)
        else:
            keys.add(full)
    return keys


def _base_keys(path: Path) -> set[str]:
    """Flattened keys with i18next plural suffixes collapsed."""
    return {_PLURAL_SUFFIX.sub("", k) for k in _flatten(_load(path))}


def _assert_parity(name_to_keys: dict[str, set[str]]) -> None:
    union: set[str] = set().union(*name_to_keys.values())
    drift = {
        name: sorted(union - keys)
        for name, keys in name_to_keys.items()
        if union - keys
    }
    assert not drift, f"Translation key drift detected: {drift}"


class TestBotTranslationParity:
    LOCALES = ("ru", "uz", "uz_cyrl")

    def test_locale_files_exist(self):
        for loc in self.LOCALES:
            assert (_BOT_DIR / f"{loc}.json").is_file()

    def test_key_sets_are_equal(self):
        keys = {loc: set(_load(_BOT_DIR / f"{loc}.json").keys()) for loc in self.LOCALES}
        _assert_parity(keys)


class TestFrontendSellerParity:
    LOCALES = ("ru", "uz", "uz-cyrl", "uz-latn")

    def test_locale_files_exist(self):
        for loc in self.LOCALES:
            assert (_FE_LOCALES / loc / "seller.json").is_file()

    def test_base_key_sets_are_equal(self):
        keys = {loc: _base_keys(_FE_LOCALES / loc / "seller.json") for loc in self.LOCALES}
        _assert_parity(keys)
