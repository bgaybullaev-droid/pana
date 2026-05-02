"""Sprint 5 — Breaking renames (T-006, T-008) with dual-read protocol.

Phase 1 of the dual-read window (blueprint §3.2):
    - ADD market_type, wall_material, furniture
    - BACKFILL: market_type ← building_type;
                furniture   ← (true → 'full', false → 'none', null → null)
    - Old columns (building_type, is_furnished) STAY in place; backend
      mirrors both names in responses; writes go to the new columns only
      (handled at the application layer, not the migration).
    - No data drop. Rollback = downgrade (drop new cols, restore unique
      ownership of old cols).

Indexes per §4.1 Sprint 5.

Revision ID: s5_dual_read_renames
Revises: s4_commercial
Create Date: 2026-04-18
"""

from alembic import op
import sqlalchemy as sa

revision = "s5_dual_read_renames"
down_revision = "s4_commercial"
branch_labels = None
depends_on = None


def _add_col(table: str, column: str, ddl: str) -> None:
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


def upgrade() -> None:
    # T-006 — market_type + wall_material
    _add_col("listings", "market_type", "VARCHAR(20)")
    _add_col("listings", "wall_material", "VARCHAR(30)")
    op.create_check_constraint(
        "ck_listings_market_type_enum",
        "listings",
        "market_type IS NULL OR market_type IN ('new','secondary')",
    )
    op.create_check_constraint(
        "ck_listings_wall_material_enum",
        "listings",
        "wall_material IS NULL OR wall_material IN "
        "('brick','gasblock','panel','monolith','other')",
    )

    # T-008 — furniture
    _add_col("listings", "furniture", "VARCHAR(20)")
    op.create_check_constraint(
        "ck_listings_furniture_enum",
        "listings",
        "furniture IS NULL OR furniture IN ('none','partial','full','built_in')",
    )

    # Backfill (idempotent — only fills NULLs)
    op.execute(
        """
        UPDATE listings
           SET market_type = building_type
         WHERE market_type IS NULL
           AND building_type IS NOT NULL
           AND building_type IN ('new', 'secondary');
        """
    )
    op.execute(
        """
        UPDATE listings
           SET furniture = CASE
               WHEN is_furnished IS TRUE  THEN 'full'
               WHEN is_furnished IS FALSE THEN 'none'
               ELSE NULL
           END
         WHERE furniture IS NULL;
        """
    )

    # Sprint 5 indexes (§4.1)
    op.create_index(
        "idx_listings_market_type",
        "listings",
        ["market_type"],
        postgresql_where=sa.text("property_type = 'APARTMENT'"),
    )
    op.create_index(
        "idx_listings_furniture",
        "listings",
        ["furniture"],
        postgresql_where=sa.text("furniture IS NOT NULL"),
    )
    op.create_index(
        "idx_listings_wall_material",
        "listings",
        ["wall_material"],
        postgresql_where=sa.text("wall_material IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_listings_wall_material", table_name="listings")
    op.drop_index("idx_listings_furniture", table_name="listings")
    op.drop_index("idx_listings_market_type", table_name="listings")
    for c in (
        "ck_listings_furniture_enum",
        "ck_listings_wall_material_enum",
        "ck_listings_market_type_enum",
    ):
        op.drop_constraint(c, "listings", type_="check")
    for col in ("furniture", "wall_material", "market_type"):
        op.execute(f"ALTER TABLE listings DROP COLUMN IF EXISTS {col};")
