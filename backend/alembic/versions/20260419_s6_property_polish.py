"""Sprint 6 — Property-type polish (T-011, T-013, T-014, T-015).

Blueprint §1.2 Sprint 6:
    - garage, basement       (house only)
    - buildings_exist, fence, land_shape  (land only)
    - balcony, listing_subtype, floor_plan_url  (apartment only)
    - widen land_purpose enum + backfill old values

Indexes per §4.1 Sprint 6.

Revision ID: s6_property_polish
Revises: s5_dual_read_renames
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "s6_property_polish"
down_revision = "s5_dual_read_renames"
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
    # T-011 house-only
    _add_col("listings", "garage", "BOOLEAN")
    _add_col("listings", "basement", "BOOLEAN")

    # T-014 land-only
    _add_col("listings", "buildings_exist", "BOOLEAN")
    _add_col("listings", "fence", "BOOLEAN")
    _add_col("listings", "land_shape", "VARCHAR(20)")
    op.create_check_constraint(
        "ck_listings_land_shape_enum",
        "listings",
        "land_shape IS NULL OR land_shape IN ('rectangular','irregular')",
    )

    # T-015 apartment-only
    _add_col("listings", "balcony", "VARCHAR(20)")
    _add_col("listings", "listing_subtype", "VARCHAR(20)")
    _add_col("listings", "floor_plan_url", "VARCHAR(500)")
    op.create_check_constraint(
        "ck_listings_balcony_enum",
        "listings",
        "balcony IS NULL OR balcony IN ('none','balcony','loggia','terrace')",
    )
    op.create_check_constraint(
        "ck_listings_listing_subtype_enum",
        "listings",
        "listing_subtype IS NULL OR listing_subtype IN "
        "('standard','studio','free_plan')",
    )

    # T-013 — widen land_purpose enum + backfill old values to new.
    # The current schema uses a free VARCHAR with no DB CHECK; we add the
    # check now (after backfilling) so existing rows don't violate it.
    op.execute(
        """
        UPDATE listings
           SET land_purpose = CASE land_purpose
               WHEN 'private'    THEN 'construction'
               WHEN 'industrial' THEN 'commercial_land'
               WHEN 'agricultural' THEN 'agricultural'
               WHEN 'commercial' THEN 'commercial_land'
               ELSE land_purpose
           END
         WHERE land_purpose IS NOT NULL;
        """
    )
    op.create_check_constraint(
        "ck_listings_land_purpose_enum",
        "listings",
        "land_purpose IS NULL OR land_purpose IN "
        "('construction','commercial_land','agricultural','garden','unspecified')",
    )

    # Sprint 6 indexes (§4.1)
    op.create_index(
        "idx_listings_garage",
        "listings",
        ["garage"],
        postgresql_where=sa.text("property_type = 'HOUSE' AND garage = true"),
    )
    op.create_index(
        "idx_listings_balcony",
        "listings",
        ["balcony"],
        postgresql_where=sa.text("property_type = 'APARTMENT' AND balcony IS NOT NULL"),
    )
    op.create_index(
        "idx_listings_listing_subtype",
        "listings",
        ["listing_subtype"],
        postgresql_where=sa.text(
            "property_type = 'APARTMENT' AND listing_subtype IS NOT NULL"
        ),
    )
    op.create_index(
        "idx_listings_land_shape",
        "listings",
        ["land_shape"],
        postgresql_where=sa.text("property_type = 'LAND' AND land_shape IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_listings_land_shape", table_name="listings")
    op.drop_index("idx_listings_listing_subtype", table_name="listings")
    op.drop_index("idx_listings_balcony", table_name="listings")
    op.drop_index("idx_listings_garage", table_name="listings")
    for c in (
        "ck_listings_land_purpose_enum",
        "ck_listings_listing_subtype_enum",
        "ck_listings_balcony_enum",
        "ck_listings_land_shape_enum",
    ):
        op.execute(f"ALTER TABLE listings DROP CONSTRAINT IF EXISTS {c};")
    for col in (
        "floor_plan_url",
        "listing_subtype",
        "balcony",
        "land_shape",
        "fence",
        "buildings_exist",
        "basement",
        "garage",
    ):
        op.execute(f"ALTER TABLE listings DROP COLUMN IF EXISTS {col};")
