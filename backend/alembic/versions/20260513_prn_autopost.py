"""PR-D4 — Block D V2.0 (D4) — channel autoposting infrastructure.

Adds the minimal schema for "bot publishes seller's listings to their
own Telegram channel as admin":

- ``sellers.autopost_channel_username`` — chat handle (e.g. ``"my_re"``).
- ``sellers.autopost_channel_id`` — numeric chat id (Telegram returns
  ``-100…`` for channels). Authoritative once verified; the username
  may rotate but the id is stable.
- ``sellers.autopost_enabled`` — opt-in / opt-out toggle.
- ``sellers.autopost_verified_at`` — when the bot last confirmed it
  could post in the channel. Cleared (NULL) when the bot is kicked
  or the channel disappears — surfaces "reconnect required" in the
  cabinet.
- ``bot_channel_posts`` — one row per (listing, channel). Tracks the
  Telegram message_id so we can edit / delete it later, and the
  ``last_listing_version`` we posted from so the cabinet can show a
  "post stale" badge when the listing has been edited since.
- ``listings.version`` (PRE-EXISTING) — small int counter bumped on
  every listing edit via the listing-update endpoint. Used for the
  staleness check; no column add needed in this migration.

Retention strategy
==================
``bot_channel_posts`` rows live as long as their parent listing — CASCADE
on listing delete. No separate pruning job needed. Expected volume:
~10K rows / month at full-MVP traffic (~1K active sellers, ~10
listings each).

Per-channel rate limit
======================
Application-level only (`services/channel_publisher.py` uses Redis
SETNX). No DB constraint on edit frequency.

Revision ID: prn_autopost
Revises: prm_behavioral_signals
Create Date: 2026-05-13
"""

from alembic import op

revision = "prn_autopost"
down_revision = "prm_behavioral_signals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='sellers' AND column_name='autopost_channel_username'
            ) THEN
                ALTER TABLE sellers
                    ADD COLUMN autopost_channel_username VARCHAR(64) NULL,
                    ADD COLUMN autopost_channel_id BIGINT NULL,
                    ADD COLUMN autopost_enabled BOOLEAN NOT NULL DEFAULT false,
                    ADD COLUMN autopost_verified_at TIMESTAMP NULL;
            END IF;
            -- listings.version already exists in initial_schema; do not add.
        END $$;
        """
    )

    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'bot_channel_posts'
            ) THEN
                CREATE TABLE bot_channel_posts (
                    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    listing_id               UUID NOT NULL
                                             REFERENCES listings(id) ON DELETE CASCADE,
                    seller_id                UUID NOT NULL
                                             REFERENCES sellers(id) ON DELETE CASCADE,
                    channel_id               BIGINT NOT NULL,
                    message_id               BIGINT NOT NULL,
                    posted_at                TIMESTAMP NOT NULL DEFAULT now(),
                    last_edited_at           TIMESTAMP NULL,
                    last_listing_version     INTEGER NOT NULL,
                    status                   VARCHAR(16) NOT NULL DEFAULT 'live'
                    -- status values: live | sold_marker | deleted
                );
                CREATE UNIQUE INDEX uq_bot_channel_posts_listing_channel
                    ON bot_channel_posts (listing_id, channel_id);
                CREATE INDEX idx_bot_channel_posts_seller_status
                    ON bot_channel_posts (seller_id, status);
                COMMENT ON TABLE bot_channel_posts IS
                    'Block D D4 — one row per (listing, channel) we have published.'
                    ' CASCADE on listing delete. Retention = listing lifetime.';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bot_channel_posts CASCADE;")
    # listings.version is owned by initial_schema — leave alone.
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='sellers' AND column_name='autopost_channel_username'
            ) THEN
                ALTER TABLE sellers
                    DROP COLUMN autopost_channel_username,
                    DROP COLUMN autopost_channel_id,
                    DROP COLUMN autopost_enabled,
                    DROP COLUMN autopost_verified_at;
            END IF;
        END $$;
        """
    )
