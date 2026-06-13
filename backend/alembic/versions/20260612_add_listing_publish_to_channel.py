"""Add listings.publish_to_channel — per-listing channel autopost opt-out.

Block D D4. Sellers get a per-listing switch controlling whether a listing
is auto-published to their connected Telegram channel. Manual listings
default to TRUE (publish); claimed / parsed imports default to FALSE so
imported content is never pushed to a channel without an explicit opt-in.

Existing rows: backfilled to FALSE for CLAIMED / PARSED source types, TRUE
for everything else (the column default).

NOTE: the ``source_type`` enum is stored by NAME — the PG enum labels are
'MANUAL' / 'CLAIMED' / 'PARSED' (see the initial schema migration), so the
backfill WHERE clause uses the uppercase labels.

Revision ID: add_listing_publish_to_channel
Revises: add_user_seller_profile
Create Date: 2026-06-12
"""

from alembic import op

revision = "add_listing_publish_to_channel"
down_revision = "add_user_seller_profile"
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
                  AND column_name = 'publish_to_channel'
            ) THEN
                ALTER TABLE listings
                    ADD COLUMN publish_to_channel BOOLEAN NOT NULL DEFAULT true;
            END IF;
        END$$;
        """
    )
    # Imported content (claimed via OLX / Telegram, or parsed) must not
    # auto-post to a channel. The enum is stored by name → uppercase labels.
    op.execute(
        """
        UPDATE listings
        SET publish_to_channel = false
        WHERE source_type IN ('CLAIMED', 'PARSED');
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'listings'
                  AND column_name = 'publish_to_channel'
            ) THEN
                ALTER TABLE listings DROP COLUMN publish_to_channel;
            END IF;
        END$$;
        """
    )
