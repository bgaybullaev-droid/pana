"""Matrix parity test — guard against drift between backend + frontend.

Per Sprint 2 technical doc §12 risk mitigation: the backend
_VISIBILITY_MATRIX MUST match the frontend VISIBILITY matrix in
frontend/src/modules/seller/feature/listing-form/lib/visibility.ts
exactly, field-for-field, combo-for-combo.

This test parses the TypeScript source with a small regex-based extractor
(no Node runtime needed) and compares the result against the backend
Python matrix. If this test ever fails, the fix is ALWAYS to sync the two
sides — never to edit this test to accept the drift.
"""

import re
from pathlib import Path

import pytest

from app.api.v1.listings import _CLEARING_VALUES as BACKEND_CLEARING_VALUES
from app.api.v1.listings import _VISIBILITY_MATRIX as BACKEND_MATRIX

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
TS_PATH = (
    REPO_ROOT
    / "frontend"
    / "src"
    / "modules"
    / "seller"
    / "feature"
    / "listing-form"
    / "lib"
    / "visibility.ts"
)

# Const names we expect to find in visibility.ts.
TS_FIELD_GROUPS = {
    "APARTMENT_BASE_FIELDS": "apartment_base",
    "HOUSE_BASE_FIELDS": "house_base",
    "COMMERCIAL_BASE_FIELDS": "commercial_base",
    "LAND_BASE_FIELDS": "land_base",
    "SALE_ONLY_FIELDS": "sale_only",
    "RENT_ONLY_FIELDS": "rent_only",
}


def _extract_string_array(source: str, const_name: str) -> list[str]:
    """Extract the list of quoted strings from a TS `const X = [...]` block."""
    # Match up to the next closing bracket. visibility.ts uses one const per
    # declaration so this is unambiguous.
    pattern = re.compile(
        rf"const\s+{re.escape(const_name)}\s*:\s*[^=]+=\s*\[(.*?)\];",
        re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        raise AssertionError(f"Could not find `const {const_name}` in {TS_PATH}")
    body = match.group(1)
    return re.findall(r'"([^"]+)"', body)


def _extract_clearing_values(source: str) -> dict[str, object]:
    """Extract the CLEARING_VALUES object from visibility.ts.

    Returns a dict mapping field_name -> one of:
        []         (empty array)
        False      (literal false)
        None       (literal undefined)
    """
    pattern = re.compile(
        r"export\s+const\s+CLEARING_VALUES\s*:\s*[^=]+=\s*\{(.*?)\};",
        re.DOTALL,
    )
    match = pattern.search(source)
    if not match:
        raise AssertionError("Could not find CLEARING_VALUES in visibility.ts")

    body = match.group(1)
    out: dict[str, object] = {}
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        if not line or line.startswith("//"):
            continue
        # Match  key: value
        m = re.match(r"(\w+)\s*:\s*(.+)", line)
        if not m:
            continue
        key, raw = m.group(1), m.group(2).strip()
        if raw == "[]":
            out[key] = []
        elif raw == "false":
            out[key] = False
        elif raw == "undefined":
            out[key] = None
        else:
            raise AssertionError(
                f"Unexpected CLEARING_VALUES entry for {key}: {raw!r}. "
                "Parity parser only supports [] / false / undefined."
            )
    return out


def _build_frontend_matrix(source: str) -> dict[tuple[str, str], frozenset]:
    """Reconstruct the (pt, dt) → frozenset matrix by combining base + group.

    Mirrors the construction in visibility.ts, not a second parse of the
    VISIBILITY object — this way both sides of the parity test are derived
    from the same source of truth (the field groups).
    """
    apt = _extract_string_array(source, "APARTMENT_BASE_FIELDS")
    house = _extract_string_array(source, "HOUSE_BASE_FIELDS")
    com = _extract_string_array(source, "COMMERCIAL_BASE_FIELDS")
    land = _extract_string_array(source, "LAND_BASE_FIELDS")
    sale = _extract_string_array(source, "SALE_ONLY_FIELDS")
    rent = _extract_string_array(source, "RENT_ONLY_FIELDS")

    return {
        ("apartment", "sell"): frozenset(apt) | frozenset(sale),
        ("apartment", "rent"): frozenset(apt) | frozenset(rent),
        ("house", "sell"): frozenset(house) | frozenset(sale),
        ("house", "rent"): frozenset(house) | frozenset(rent),
        ("commercial", "sell"): frozenset(com) | frozenset(sale),
        ("commercial", "rent"): frozenset(com) | frozenset(rent),
        ("land", "sell"): frozenset(land) | frozenset(sale),
        ("land", "rent"): frozenset(land) | frozenset(rent),
    }


@pytest.fixture(scope="module")
def ts_source() -> str:
    assert TS_PATH.exists(), f"visibility.ts not found at {TS_PATH}"
    return TS_PATH.read_text(encoding="utf-8")


class TestMatrixParity:
    def test_all_combos_match(self, ts_source: str):
        frontend = _build_frontend_matrix(ts_source)
        for combo, fe_fields in frontend.items():
            be_fields = BACKEND_MATRIX[combo]
            missing_in_backend = fe_fields - be_fields
            missing_in_frontend = be_fields - fe_fields
            assert not missing_in_backend and not missing_in_frontend, (
                f"Matrix drift for {combo}:\n"
                f"  only in frontend: {sorted(missing_in_backend)}\n"
                f"  only in backend:  {sorted(missing_in_frontend)}"
            )

    def test_backend_has_no_extra_combos(self, ts_source: str):
        """Backend must not carry combos the frontend doesn't know about."""
        frontend = _build_frontend_matrix(ts_source)
        extra = set(BACKEND_MATRIX.keys()) - set(frontend.keys())
        assert (
            not extra
        ), f"Backend matrix has combos absent from frontend: {sorted(extra)}"


class TestClearingValuesParity:
    def test_keys_match(self, ts_source: str):
        frontend = _extract_clearing_values(ts_source)
        fe_keys = set(frontend.keys())
        be_keys = set(BACKEND_CLEARING_VALUES.keys())
        assert fe_keys == be_keys, (
            "CLEARING_VALUES field set drift:\n"
            f"  only in frontend: {sorted(fe_keys - be_keys)}\n"
            f"  only in backend:  {sorted(be_keys - fe_keys)}"
        )

    def test_values_match(self, ts_source: str):
        """Both sides must agree on the canonical empty value per field.

        Mapping convention (already mutually consistent):
            frontend []        ↔ backend None   (NULL-array)
            frontend false     ↔ backend False
            frontend undefined ↔ backend None
        """
        frontend = _extract_clearing_values(ts_source)
        for field, fe_val in frontend.items():
            be_val = BACKEND_CLEARING_VALUES[field]
            if fe_val == []:
                # Both sides agree this is an array-typed column cleared to NULL.
                assert be_val is None, (
                    f"{field}: frontend clears to [], backend should clear to "
                    f"None; got {be_val!r}"
                )
            elif fe_val is False:
                assert be_val is False, (
                    f"{field}: frontend clears to false, backend must clear "
                    f"to False (DB column is NOT NULL); got {be_val!r}"
                )
            elif fe_val is None:  # undefined
                assert be_val is None, (
                    f"{field}: frontend clears to undefined, backend must "
                    f"clear to None; got {be_val!r}"
                )
            else:
                pytest.fail(f"Unexpected frontend CLEARING_VALUES[{field}]={fe_val!r}")
