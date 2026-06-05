"""PR-G — Landmark catalog + geo-aware housing complexes.

Adds the reference catalogs that back the seller form's address hints:

  - new table ``landmarks`` (markets, malls, universities, parks, stations…),
    pinned to a district key from REGIONS, with multilingual names and a
    WGS-84 point. Seeded from OpenStreetMap.
  - ``housing_complexes`` gains the same geo/i18n columns so it can hold
    coordinates, a microdistrict pin, Uzbek names and OSM/listing provenance.
  - ``listings.landmark_id`` — optional FK to ``landmarks`` (coexists with the
    free-text ``landmark`` column, mirroring jk_id / jk_name).

All DDL is idempotent (IF NOT EXISTS / information_schema guards) so the
auto-applied ``alembic upgrade head`` on deploy is safe to re-run.

Revision ID: landmarks_and_hc_geo
Revises: rename_city_district_keys
Create Date: 2026-06-05
"""

from alembic import op

# revision identifiers
revision = "landmarks_and_hc_geo"
down_revision = "rename_city_district_keys"
branch_labels = None
depends_on = None


def _add_col(table: str, column: str, ddl: str) -> None:
    """Add a column only if it does not already exist (idempotent)."""
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = '{column}'
            ) THEN
                ALTER TABLE {table} ADD COLUMN {column} {ddl};
            END IF;
        END $$;
        """
    )


# Geo + i18n + provenance columns shared by housing_complexes and landmarks.
_GEO_COLS = (
    ("name_uz_latn", "VARCHAR(200)"),
    ("name_uz_cyrl", "VARCHAR(200)"),
    ("microdistrict", "VARCHAR(100)"),
    ("latitude", "DOUBLE PRECISION"),
    ("longitude", "DOUBLE PRECISION"),
    ("osm_id", "VARCHAR(50)"),
    ("source", "VARCHAR(20) NOT NULL DEFAULT 'osm'"),
)


def upgrade() -> None:
    # 1) housing_complexes — geo/i18n/provenance columns
    for col, ddl in _GEO_COLS:
        _add_col("housing_complexes", col, ddl)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_housing_complexes_osm_id "
        "ON housing_complexes(osm_id) WHERE osm_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_housing_complexes_district "
        "ON housing_complexes(district);"
    )

    # 2) landmarks — new reference catalog
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS landmarks (
            id UUID PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            name_uz_latn VARCHAR(200) NULL,
            name_uz_cyrl VARCHAR(200) NULL,
            category VARCHAR(50) NULL,
            region VARCHAR(100) NULL,
            district VARCHAR(100) NULL,
            microdistrict VARCHAR(100) NULL,
            latitude DOUBLE PRECISION NULL,
            longitude DOUBLE PRECISION NULL,
            osm_id VARCHAR(50) NULL,
            source VARCHAR(20) NOT NULL DEFAULT 'osm',
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_landmarks_district ON landmarks(district);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_landmarks_region ON landmarks(region);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_landmarks_category ON landmarks(category);"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_landmarks_osm_id "
        "ON landmarks(osm_id) WHERE osm_id IS NOT NULL;"
    )

    # 3) listings.landmark_id — optional FK (dual-column with free-text landmark)
    _add_col(
        "listings",
        "landmark_id",
        "UUID NULL REFERENCES landmarks(id) ON DELETE SET NULL",
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_listings_landmark_id "
        "ON listings(landmark_id) WHERE landmark_id IS NOT NULL;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_listings_landmark_id;")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS landmark_id;")
    op.execute("DROP TABLE IF EXISTS landmarks;")
    op.execute("DROP INDEX IF EXISTS idx_housing_complexes_district;")
    op.execute("DROP INDEX IF EXISTS uq_housing_complexes_osm_id;")
    for col, _ddl in _GEO_COLS:
        op.execute(f"ALTER TABLE housing_complexes DROP COLUMN IF EXISTS {col};")
