"""Sprint 4 — Commercial overhaul (T-009) + condition enum widen (T-007).

Blueprint §1.2 Sprint 4. 6 new commercial-only columns + condition enum
widening (no DB-level enum, only Pydantic; check constraint widened).

Indexes per §4.1 Sprint 4. All non-destructive.

Revision ID: s4_commercial
Revises: s3_location_fields
Create Date: 2026-04-17
"""

from alembic import op
import sqlalchemy as sa

revision = "s4_commercial"
down_revision = "s3_location_fields"
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
    # T-009 commercial columns
    _add_col("listings", "commercial_type", "VARCHAR(30)")
    _add_col("listings", "price_per_sqm", "BIGINT")
    _add_col("listings", "ceiling_height", "FLOAT")
    _add_col("listings", "entrance", "VARCHAR(30)")
    _add_col("listings", "parking_comm", "BOOLEAN")
    _add_col("listings", "building_class", "VARCHAR(30)")

    # CHECK constraints
    op.create_check_constraint(
        "ck_listings_commercial_type_enum",
        "listings",
        "commercial_type IS NULL OR commercial_type IN "
        "('office','shop','warehouse','production','restaurant','hotel','other')",
    )
    op.create_check_constraint(
        "ck_listings_price_per_sqm_nonneg",
        "listings",
        "price_per_sqm IS NULL OR price_per_sqm >= 0",
    )
    op.create_check_constraint(
        "ck_listings_ceiling_height_range",
        "listings",
        "ceiling_height IS NULL OR (ceiling_height > 0 AND ceiling_height <= 30)",
    )
    op.create_check_constraint(
        "ck_listings_entrance_enum",
        "listings",
        "entrance IS NULL OR entrance IN ('separate','yard','street','mall')",
    )
    op.create_check_constraint(
        "ck_listings_building_class_enum",
        "listings",
        "building_class IS NULL OR building_class IN "
        "('standalone','embedded','business_center','mall')",
    )

    # T-007: condition enum widen — current constraint allowed
    # (euro|cosmetic|needs_repair|rough|none); new set adds shell, medium,
    # designer, turnkey, needs_repair_comm.
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_listings_condition_enum'
            ) THEN
                ALTER TABLE listings DROP CONSTRAINT ck_listings_condition_enum;
            END IF;
        END $$;
        """
    )
    op.create_check_constraint(
        "ck_listings_condition_enum",
        "listings",
        "condition IS NULL OR condition IN "
        "('shell','none','cosmetic','medium','euro','designer',"
        "'turnkey','needs_repair_comm','needs_repair','rough')",
    )

    # Sprint 4 indexes (§4.1)
    op.create_index(
        "idx_listings_commercial_type",
        "listings",
        ["commercial_type"],
        postgresql_where=sa.text("property_type = 'COMMERCIAL'"),
    )
    op.create_index(
        "idx_listings_building_class",
        "listings",
        ["building_class"],
        postgresql_where=sa.text("property_type = 'COMMERCIAL'"),
    )
    op.create_index(
        "idx_listings_ceiling_height",
        "listings",
        ["ceiling_height"],
        postgresql_where=sa.text(
            "property_type = 'COMMERCIAL' AND ceiling_height IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index("idx_listings_ceiling_height", table_name="listings")
    op.drop_index("idx_listings_building_class", table_name="listings")
    op.drop_index("idx_listings_commercial_type", table_name="listings")

    # Restore the original (pre-S4) condition CHECK
    op.execute(
        "ALTER TABLE listings DROP CONSTRAINT IF EXISTS ck_listings_condition_enum"
    )
    op.create_check_constraint(
        "ck_listings_condition_enum",
        "listings",
        "condition IS NULL OR condition IN "
        "('euro','cosmetic','needs_repair','rough','none')",
    )

    for c in (
        "ck_listings_building_class_enum",
        "ck_listings_entrance_enum",
        "ck_listings_ceiling_height_range",
        "ck_listings_price_per_sqm_nonneg",
        "ck_listings_commercial_type_enum",
    ):
        op.drop_constraint(c, "listings", type_="check")
    for col in (
        "building_class",
        "parking_comm",
        "entrance",
        "ceiling_height",
        "price_per_sqm",
        "commercial_type",
    ):
        op.execute(f"ALTER TABLE listings DROP COLUMN IF EXISTS {col};")
