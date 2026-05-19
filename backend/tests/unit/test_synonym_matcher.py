"""Block F V2.0 F2 — synonym matcher unit tests.

Pure-function tests against a stubbed DB session that returns canned
``SynonymEntry`` rows. Covers: present/absent matching, contradiction
detection, negation (5-token window), enum-value comparison, and
first-match-wins deduplication.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.synonym_matcher import (
    SynonymMatch,
    _detect_polarity,
    match_text_to_params,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@dataclass
class _Row:
    parameter_key: str
    parameter_value: Optional[str]
    surface_form: str
    language: str
    polarity: str = "positive"


def _db_with(rows: list[_Row]):
    async def fake_execute(stmt):
        result = MagicMock()
        scalars = MagicMock()
        scalars.all.return_value = rows
        result.scalars.return_value = scalars
        return result

    db = MagicMock()
    db.execute = AsyncMock(side_effect=fake_execute)
    return db


class TestPolarityWindow:
    def test_no_negation(self):
        assert _detect_polarity("есть кондиционер", 5, "positive") == "positive"

    def test_negation_не(self):
        assert _detect_polarity("без кондиционера", 4, "positive") == "negative"

    def test_negation_yo_q(self):
        assert _detect_polarity("kondisioner yo'q", 0, "positive") == "positive"
        # Negation appears after the match — not in the *preceding*
        # 5-token window — so polarity stays positive.

    def test_negation_outside_window(self):
        # 10 tokens of buffer before the negation — outside the 5-token
        # window so polarity is unchanged.
        text = "не " + " ".join(["word"] * 8) + " кондиционер"
        pos = text.find("кондиционер")
        assert _detect_polarity(text, pos, "positive") == "positive"


class TestMatcher:
    async def test_present_unchecked_returns_add(self):
        db = _db_with(
            [_Row("air_conditioner", None, "кондиционер", "ru")]
        )
        out = await match_text_to_params(
            db, "У квартиры есть кондиционер.", "ru", {}
        )
        assert len(out) == 1
        assert out[0].action == "add"
        assert out[0].parameter_key == "air_conditioner"

    async def test_present_already_checked_filtered_out(self):
        db = _db_with(
            [_Row("air_conditioner", None, "кондиционер", "ru")]
        )
        out = await match_text_to_params(
            db, "У квартиры есть кондиционер.", "ru", {"air_conditioner": True}
        )
        assert out == []  # "ok" matches are dropped

    async def test_contradict_enum(self):
        db = _db_with(
            [_Row("furniture", "full", "с мебелью", "ru")]
        )
        out = await match_text_to_params(
            db, "Квартира с мебелью.", "ru", {"furniture": "none"}
        )
        assert len(out) == 1
        assert out[0].action == "contradict"

    async def test_negation_flips_polarity(self):
        db = _db_with(
            [_Row("air_conditioner", None, "кондиционер", "ru")]
        )
        out = await match_text_to_params(
            db, "Без кондиционера, без газа.", "ru", {"air_conditioner": True}
        )
        assert len(out) == 1
        assert out[0].polarity == "negative"
        assert out[0].action == "contradict"

    async def test_dedup_by_parameter_key(self):
        db = _db_with(
            [
                _Row("air_conditioner", None, "кондиционер", "ru"),
                _Row("air_conditioner", None, "кондей", "ru"),
                _Row("air_conditioner", None, "сплит", "ru"),
            ]
        )
        out = await match_text_to_params(
            db, "Кондиционер, кондей и сплит.", "ru", {}
        )
        # Only first match wins for any given parameter_key.
        assert len(out) == 1

    async def test_wildcard_language(self):
        db = _db_with(
            [_Row("internet", None, "wi-fi", "*")]
        )
        out = await match_text_to_params(db, "Есть Wi-Fi.", "ru", {})
        assert len(out) == 1
        assert out[0].parameter_key == "internet"

    async def test_empty_text_returns_empty(self):
        db = _db_with([_Row("balcony", None, "балкон", "ru")])
        assert await match_text_to_params(db, "", "ru", {}) == []
        assert await match_text_to_params(db, "   ", "ru", {}) == []

    async def test_caps_at_20(self):
        rows = [
            _Row(f"key_{i:02d}", None, f"surface_{i:02d}", "ru")
            for i in range(30)
        ]
        text = " ".join(f"surface_{i:02d}" for i in range(30))
        db = _db_with(rows)
        out = await match_text_to_params(db, text, "ru", {})
        assert len(out) <= 20
