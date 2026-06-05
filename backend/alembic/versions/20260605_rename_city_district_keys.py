"""Rename city/district keys to the SOATO _sh/_t convention.

Cities of regional subordination now use the `_sh` suffix and their
same-name districts the `_t` suffix (mirrors frontend regions.ts and
backend app/core/regions.py). This migration remaps the stored
``district`` values of existing rows so they keep pointing at the same
unit after the key rename.

Mapping rationale (faithful to the OLD displayed label):
  - keys previously shown as a CITY  → ``*_sh`` (city of regional subordination)
  - keys previously shown as a DISTRICT (``…р-н``) → ``*_t`` (tuman)
  - ``bo_z`` → ``bo_ston`` (official rename Boʻz → Boʻston)

Region values are unchanged; only the district key string is rewritten.
``microdistrict`` (free-text name) and ``metro_station`` (own keys) are
unaffected.

Revision ID: rename_city_district_keys
Revises: merge_phase2_and_prp_v2
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "rename_city_district_keys"
down_revision = "merge_phase2_and_prp_v2"
branch_labels = None
depends_on = None

# Tables carrying a district key (see backend/scripts/backfill_location.py).
TABLES = ("listings", "telegram_listings", "olx_listings")

# old district key → new key
RENAME = {
    # previously shown as a city → city of regional subordination (_sh)
    "nurafshon": "nurafshon_sh",
    "olmaliq": "olmaliq_sh",
    "angren": "angren_sh",
    "bekobod": "bekobod_sh",
    "chirchiq": "chirchiq_sh",
    "ohangaron": "ohangaron_sh",
    "yangiyo_l": "yangiyo_l_sh",
    "marg_ilon": "marg_ilon_sh",
    "quvasoy": "quvasoy_sh",
    "xonobod": "xonobod_sh",
    # previously shown as a district (…р-н) → tuman (_t)
    "kattaqo_rg_on": "kattaqo_rg_on_t",
    "kogon": "kogon_t",
    "shahrisabz": "shahrisabz_t",
    "xiva": "xiva_t",
    # official rename
    "bo_z": "bo_ston",
}


def _remap(mapping: dict[str, str]) -> None:
    conn = op.get_bind()
    for table in TABLES:
        for old, new in mapping.items():
            conn.execute(
                sa.text(
                    f"UPDATE {table} SET district = :new WHERE district = :old"
                ),
                {"new": new, "old": old},
            )


def upgrade() -> None:
    _remap(RENAME)


def downgrade() -> None:
    _remap({new: old for old, new in RENAME.items()})
