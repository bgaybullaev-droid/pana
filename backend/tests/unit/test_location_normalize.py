"""PR-G — unit tests for complex/landmark name normalization (dedup key)."""

from __future__ import annotations

import pytest

from app.core.location_normalize import normalize_complex_name

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("ЖК BAROCCO", "barocco"),
        ("BAROCCO", "barocco"),
        ('ЖК "Barocco"', "barocco"),
        ("Akay City TJM", "akay city"),
        ("ЖК Akay City", "akay city"),
        ("жилой комплекс Новый век", "новый век"),
        ("  Manhattan  ", "manhattan"),
        ("ЖК", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_normalize_collapses_markers(raw, expected):
    assert normalize_complex_name(raw) == expected


def test_variants_dedup_together():
    keys = {
        normalize_complex_name(x)
        for x in ['ЖК BAROCCO', "BAROCCO", 'ЖК "Barocco"', "  barocco "]
    }
    assert keys == {"barocco"}
