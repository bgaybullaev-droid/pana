"""Block D D4 — record the last channel-publish attempt outcome on sellers.

Adds two nullable columns to ``sellers`` so the cabinet can show *why* a
listing did (or didn't) reach the channel without anyone reading worker logs:

- ``autopost_last_result``    — ``"ok"`` or a reason/error code written by the
  publish Celery task (``bad_request`` / ``forbidden`` / ``listing_not_active``
  / ``publish_opt_out`` / ``already_posted`` …).
- ``autopost_last_result_at`` — when that attempt ran. A timestamp that does
  NOT advance after a save signals the worker isn't processing (deploy issue),
  not a Telegram problem.

Idempotent: guarded by information_schema so re-runs are safe.

Revision ID: autopost_last_result
Revises: add_listing_publish_to_channel
Create Date: 2026-06-13
"""

from alembic import op

revision = "autopost_last_result"
down_revision = "add_listing_publish_to_channel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='sellers' AND column_name='autopost_last_result'
            ) THEN
                ALTER TABLE sellers
                    ADD COLUMN autopost_last_result VARCHAR(64) NULL,
                    ADD COLUMN autopost_last_result_at TIMESTAMP NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='sellers' AND column_name='autopost_last_result'
            ) THEN
                ALTER TABLE sellers
                    DROP COLUMN autopost_last_result,
                    DROP COLUMN autopost_last_result_at;
            END IF;
        END $$;
        """
    )
