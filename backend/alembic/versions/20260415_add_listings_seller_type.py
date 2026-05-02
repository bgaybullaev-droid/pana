"""Backfill the missing Alembic migration for `listings.seller_type`.

The column was added to the SQLAlchemy model in commit daf4368 (map +
location work) without a matching migration. The remote production DB
already has it (added by hand at the time); fresh / staging databases
were missing it, which broke ListingResponse on bare `alembic upgrade
head`.

This migration is IDEMPOTENT — it uses information_schema to detect the
column before issuing ADD COLUMN, so it's safe on every environment:
    - fresh DB: adds the column
    - prod / staging where the column already exists: no-op

Revision ID: add_listings_seller_type
Revises: sprint2_rent_sale_finance
Create Date: 2026-04-15
"""

from alembic import op

revision = "add_listings_seller_type"
down_revision = "sprint2_rent_sale_finance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'listings'
                  AND column_name = 'seller_type'
            ) THEN
                ALTER TABLE listings
                ADD COLUMN seller_type VARCHAR(20);
            END IF;
        END$$;
        """
    )


def downgrade() -> None:
    # Conditional drop so downgrading on a DB that NEVER had the column
    # (post-fresh-install) doesn't fail.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'listings'
                  AND column_name = 'seller_type'
            ) THEN
                ALTER TABLE listings DROP COLUMN seller_type;
            END IF;
        END$$;
        """
    )
