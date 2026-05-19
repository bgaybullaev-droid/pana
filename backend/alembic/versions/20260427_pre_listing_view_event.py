"""PR-E — listing_view_event log for personalisation + dashboard events.

Stores per-user view / contact / share events. Anonymous traffic does
NOT write here — it bumps the cached counters on listings instead.
Aggregate seller-dashboard reads still use cached counters; this table
is the canonical event log for personalisation.

Schema mirrors ``ListingViewEvent`` in ``backend/app/db/models.py``.
The dedup index is functional + partial and is therefore created via
raw SQL (SQLAlchemy can't express the combo declaratively).

Additive, idempotent.

Revision ID: pre_listing_view_event
Revises: prd_crawled_claim_reject
Create Date: 2026-04-27
"""

from alembic import op

revision = "pre_listing_view_event"
down_revision = "prd_crawled_claim_reject"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'listing_view_event'
            ) THEN
                CREATE TABLE listing_view_event (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
                    listing_id  UUID NOT NULL,
                    event_type  VARCHAR(16) NOT NULL,
                    viewed_at   TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                    dwell_ms    BIGINT
                );

                CREATE INDEX idx_listing_view_event_user_time
                    ON listing_view_event (user_id, viewed_at DESC)
                    WHERE user_id IS NOT NULL;

                CREATE INDEX idx_listing_view_event_listing_type_time
                    ON listing_view_event (listing_id, event_type, viewed_at DESC);

                -- Dedup: at most one row per (user, listing, type, calendar-day).
                -- Partial — anonymous (user_id IS NULL) skipped, never written.
                CREATE UNIQUE INDEX uq_listing_view_event_dedup
                    ON listing_view_event (user_id, listing_id, event_type, (date(viewed_at)))
                    WHERE user_id IS NOT NULL;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS listing_view_event CASCADE")
