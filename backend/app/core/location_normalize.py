"""Name normalization for matching free-text complex / landmark names
against the reference catalog.

Used by the OSM-seed dedup step to decide whether a listing's free-text
`jk_name` already exists in `housing_complexes`. Pure and dependency-free
so it can be unit-tested without a DB or backend packages.

Examples (all collapse to the same key, so they dedup together):
    "ЖК BAROCCO"  ·  "BAROCCO"  ·  'ЖК "Barocco"'   → "barocco"
    "Akay City TJM"  ·  "ЖК Akay City"              → "akay city"
"""

from __future__ import annotations

import re

# Leading/trailing "this is a residential complex" markers to strip.
_MARKERS = (
    "жилой комплекс",
    "residential complex",
    "turar joy majmuasi",
    "turar-joy majmuasi",
    "ж/к",
    "жк",
    "tjm",
)


def normalize_complex_name(name: str | None) -> str:
    """Return a comparison key: lower-cased, punctuation/quotes flattened,
    and surrounding complex markers (ЖК / TJM / жилой комплекс …) removed."""
    if not name:
        return ""
    s = name.strip().lower()
    # Flatten quotes, apostrophe variants and separators to spaces.
    for ch in ("«", "»", '"', "'", "ʻ", "‘", "’", "`"):
        s = s.replace(ch, " ")
    s = re.sub(r"[\-_/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Strip markers from both ends, repeatedly (handles "ЖК … TJM").
    changed = True
    while changed:
        changed = False
        for mk in _MARKERS:
            if s == mk:
                return ""
            if s.startswith(mk + " "):
                s = s[len(mk) + 1 :].strip()
                changed = True
            if s.endswith(" " + mk):
                s = s[: -(len(mk) + 1)].strip()
                changed = True
    return re.sub(r"\s+", " ", s).strip()
