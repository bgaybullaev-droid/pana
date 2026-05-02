"""PR-D — add claim/reject tracking to crawled listings.

- telegram_listings: converted_listing_id (FK to listings), rejected_by_seller_id (FK to sellers), rejected_at
- olx_listings: rejected_by_seller_id (FK to sellers), rejected_at

Lets sellers claim crawled listings (convert to Listing) and hide
rejected ones from their "Topilganlar" feed.

Additive, idempotent.

Revision ID: prd_crawled_claim_reject
Revises: prc_notification_source
Create Date: 2026-04-26
"""

from alembic import op

revision = "prd_crawled_claim_reject"
down_revision = "prc_notification_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'telegram_listings' AND column_name = 'converted_listing_id'
            ) THEN
                ALTER TABLE telegram_listings
                    ADD COLUMN converted_listing_id UUID REFERENCES listings(id) ON DELETE SET NULL;
                CREATE UNIQUE INDEX uq_telegram_converted_listing
                    ON telegram_listings (converted_listing_id)
                    WHERE converted_listing_id IS NOT NULL;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'telegram_listings' AND column_name = 'rejected_by_seller_id'
            ) THEN
                ALTER TABLE telegram_listings
                    ADD COLUMN rejected_by_seller_id UUID REFERENCES sellers(id) ON DELETE SET NULL,
                    ADD COLUMN rejected_at TIMESTAMP NULL;
                CREATE INDEX ix_telegram_rejected_by_seller
                    ON telegram_listings (rejected_by_seller_id)
                    WHERE rejected_by_seller_id IS NOT NULL;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'olx_listings' AND column_name = 'rejected_by_seller_id'
            ) THEN
                ALTER TABLE olx_listings
                    ADD COLUMN rejected_by_seller_id UUID REFERENCES sellers(id) ON DELETE SET NULL,
                    ADD COLUMN rejected_at TIMESTAMP NULL;
                CREATE INDEX ix_olx_rejected_by_seller
                    ON olx_listings (rejected_by_seller_id)
                    WHERE rejected_by_seller_id IS NOT NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE telegram_listings DROP COLUMN IF EXISTS converted_listing_id;
        ALTER TABLE telegram_listings DROP COLUMN IF EXISTS rejected_by_seller_id;
        ALTER TABLE telegram_listings DROP COLUMN IF EXISTS rejected_at;
        ALTER TABLE olx_listings DROP COLUMN IF EXISTS rejected_by_seller_id;
        ALTER TABLE olx_listings DROP COLUMN IF EXISTS rejected_at;
        DROP INDEX IF EXISTS uq_telegram_converted_listing;
        DROP INDEX IF EXISTS ix_telegram_rejected_by_seller;
        DROP INDEX IF EXISTS ix_olx_rejected_by_seller;
        """
    )
