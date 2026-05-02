"""Sprint 3 — Cross-cutting location (T-001) + seller_telegram + seller_type
enum extension (add `developer`).

Blueprint §1.2 Sprint 3. All columns nullable; non-destructive. Indexes per
§4.1 Sprint 3. Uses IF NOT EXISTS for idempotency where supported.

Revision ID: s3_location_fields
Revises: add_listings_seller_type
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa

revision = "s3_location_fields"
down_revision = "add_listings_seller_type"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: str, ddl: str) -> None:
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
    # T-001 columns
    _add_column_if_missing("listings", "urgent_flag", "BOOLEAN NOT NULL DEFAULT false")
    _add_column_if_missing("listings", "city", "VARCHAR(100)")
    _add_column_if_missing("listings", "microdistrict", "VARCHAR(200)")
    _add_column_if_missing("listings", "jk_name", "VARCHAR(200)")
    _add_column_if_missing("listings", "landmark", "VARCHAR(500)")
    _add_column_if_missing("listings", "metro_station", "VARCHAR(50)")
    _add_column_if_missing("listings", "seller_telegram", "VARCHAR(100)")

    # Indexes (blueprint §4.1 Sprint 3)
    op.create_index(
        "idx_listings_urgent_flag",
        "listings",
        ["urgent_flag"],
        postgresql_where=sa.text("urgent_flag = true"),
    )
    op.create_index(
        "idx_listings_metro_station",
        "listings",
        ["metro_station"],
        postgresql_where=sa.text("metro_station IS NOT NULL"),
    )
    op.create_index(
        "idx_listings_microdistrict",
        "listings",
        ["microdistrict"],
        postgresql_where=sa.text("microdistrict IS NOT NULL"),
    )
    op.create_index(
        "idx_listings_jk_name",
        "listings",
        ["jk_name"],
        postgresql_where=sa.text("jk_name IS NOT NULL"),
    )

    # Seller_type is VARCHAR in this schema (no enum type), so no DDL
    # change needed — validator catches the new value. (T-001 enum extension
    # lives in the Pydantic pattern; see ListingBase.)


def downgrade() -> None:
    op.drop_index("idx_listings_jk_name", table_name="listings")
    op.drop_index("idx_listings_microdistrict", table_name="listings")
    op.drop_index("idx_listings_metro_station", table_name="listings")
    op.drop_index("idx_listings_urgent_flag", table_name="listings")
    for col in (
        "seller_telegram",
        "metro_station",
        "landmark",
        "jk_name",
        "microdistrict",
        "city",
        "urgent_flag",
    ):
        op.execute(f"ALTER TABLE listings DROP COLUMN IF EXISTS {col};")
