"""PR-G — seed landmarks & housing complexes from OSM + dedup listing jk_name.

Loads the JSON seeds produced by ``backend/scripts/seed_locations_from_osm.py``
(committed under ``backend/app/data/``) into the ``landmarks`` and
``housing_complexes`` tables, then back-fills ``housing_complexes`` with any
free-text ``listings.jk_name`` values that are not already represented.

Why a data migration: the seed must be applied automatically on deploy
(``alembic upgrade head`` on the VPS), where the production DB lives — the
build session can't reach it. The listing-name dedup therefore also runs
there. Everything is idempotent:

  - OSM rows dedup on the partial unique index ``(osm_id) WHERE osm_id IS NOT NULL``.
  - listing rows dedup on a normalized-name key against existing rows.

If the seed files are missing (e.g. after a downgrade) the OSM load is a
no-op; the dedup still runs.

Revision ID: seed_locations
Revises: landmarks_and_hc_geo
Create Date: 2026-06-05
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from alembic import op
from sqlalchemy import text

revision = "seed_locations"
down_revision = "landmarks_and_hc_geo"
branch_labels = None
depends_on = None

_DATA_DIR = Path(__file__).resolve().parents[2] / "app" / "data"

# Self-contained copy of app.core.location_normalize.normalize_complex_name —
# migrations must not depend on app code that may change after this revision.
_MARKERS = (
    "жилой комплекс",
    "residential complex",
    "turar joy majmuasi",
    "turar-joy majmuasi",
    "ж/к",
    "жк",
    "tjm",
)


def _norm(name: str | None) -> str:
    if not name:
        return ""
    s = name.strip().lower()
    for ch in ("«", "»", '"', "'", "ʻ", "‘", "’", "`"):
        s = s.replace(ch, " ")
    s = re.sub(r"[\-_/]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
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


def _load(name: str) -> list[dict]:
    path = _DATA_DIR / name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def upgrade() -> None:
    conn = op.get_bind()

    # 1) landmarks (OSM) — idempotent on osm_id
    landmarks = _load("landmarks_seed.json")
    if landmarks:
        stmt = text(
            "INSERT INTO landmarks (id, name, name_uz_latn, name_uz_cyrl, "
            "category, region, district, microdistrict, latitude, longitude, "
            "osm_id, source) VALUES (:id, :name, :nl, :nc, :cat, :region, "
            ":district, :micro, :lat, :lng, :osm_id, :source) "
            "ON CONFLICT (osm_id) WHERE osm_id IS NOT NULL DO NOTHING"
        )
        conn.execute(
            stmt,
            [
                {
                    "id": str(uuid.uuid4()),
                    "name": r["name"],
                    "nl": r.get("name_uz_latn"),
                    "nc": r.get("name_uz_cyrl"),
                    "cat": r.get("category"),
                    "region": r.get("region"),
                    "district": r.get("district"),
                    "micro": r.get("microdistrict"),
                    "lat": r.get("latitude"),
                    "lng": r.get("longitude"),
                    "osm_id": r.get("osm_id"),
                    "source": r.get("source", "osm"),
                }
                for r in landmarks
            ],
        )

    # 2) housing_complexes (OSM) — idempotent on osm_id
    housing = _load("housing_complexes_seed.json")
    if housing:
        stmt = text(
            "INSERT INTO housing_complexes (id, name, name_uz_latn, "
            "name_uz_cyrl, region, district, microdistrict, latitude, "
            "longitude, osm_id, source) VALUES (:id, :name, :nl, :nc, "
            ":region, :district, :micro, :lat, :lng, :osm_id, :source) "
            "ON CONFLICT (osm_id) WHERE osm_id IS NOT NULL DO NOTHING"
        )
        conn.execute(
            stmt,
            [
                {
                    "id": str(uuid.uuid4()),
                    "name": r["name"],
                    "nl": r.get("name_uz_latn"),
                    "nc": r.get("name_uz_cyrl"),
                    "region": r.get("region"),
                    "district": r.get("district"),
                    "micro": r.get("microdistrict"),
                    "lat": r.get("latitude"),
                    "lng": r.get("longitude"),
                    "osm_id": r.get("osm_id"),
                    "source": r.get("source", "osm"),
                }
                for r in housing
            ],
        )

    # 3) Dedup: promote distinct listing jk_name values not already present.
    #    Runs on the VPS (where listings have data); a no-op in an empty DB.
    existing = {
        _norm(row[0])
        for row in conn.execute(text("SELECT name FROM housing_complexes")).fetchall()
    }
    existing.discard("")
    jk_rows = conn.execute(
        text(
            "SELECT DISTINCT ON (jk_name) jk_name, region, district, "
            "microdistrict, latitude, longitude FROM listings "
            "WHERE jk_name IS NOT NULL AND btrim(jk_name) <> '' "
            "AND district IS NOT NULL ORDER BY jk_name, created_at DESC"
        )
    ).fetchall()
    new_rows = []
    for jk_name, region, district, micro, lat, lng in jk_rows:
        key = _norm(jk_name)
        if not key or key in existing:
            continue
        existing.add(key)
        new_rows.append(
            {
                "id": str(uuid.uuid4()),
                "name": jk_name.strip(),
                "region": region,
                "district": district,
                "micro": micro,
                "lat": lat,
                "lng": lng,
            }
        )
    if new_rows:
        conn.execute(
            text(
                "INSERT INTO housing_complexes (id, name, region, district, "
                "microdistrict, latitude, longitude, source) VALUES "
                "(:id, :name, :region, :district, :micro, :lat, :lng, 'listing')"
            ),
            new_rows,
        )


def downgrade() -> None:
    # Only remove catalog-seeded rows; listing-derived rows are user data.
    op.execute("DELETE FROM landmarks WHERE source = 'osm';")
    op.execute("DELETE FROM housing_complexes WHERE source IN ('osm', 'listing');")
