"""PR-D2 — Block D V2.0 (D2) — behavioral_signals append-only table.

Single observation table the recommender (Ф-77 / Ф-78) reads from.
Sources today are 'push_inline' (bot inline buttons) and 'in_app'
(TWA favorites endpoint); D5 will add 'bot_search' and 'inline_mode'
later. ``event_type`` is the verb the user performed, ``source`` is
where they performed it.

Retention strategy (operational, not application-enforced)
==========================================================
- **180 days raw**; older rows pruned by a nightly cron:
    DELETE FROM behavioral_signals WHERE created_at < NOW() - INTERVAL '180 days';
  Range-scans the (created_at) part of idx_signals_user_created.
- **Aggregate to weekly buckets** if recommender needs longer history.
- **Estimated growth**: ~2K rows/day at 10% push engagement (~20K
  pushes/day) ≈ ~720K rows/year ≈ ~720 MB raw. Single index DB-fits.

Degraded behavior
=================
- Redis NX dedup (in `services/behavioral_signals.py`) is best-effort.
  When Redis is unavailable, duplicate rows from tap-storms slip
  through; the table tolerates this (recommender treats events as
  independent observations).
- DB-write failures inside the writer are logged at WARNING and
  swallowed — analytics must never break a user action.

Revision ID: prm_behavioral_signals
Revises: prl_deep_link_payloads
Create Date: 2026-05-13
"""

from alembic import op

revision = "prm_behavioral_signals"
down_revision = "prl_deep_link_payloads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'behavioral_signals'
            ) THEN
                CREATE TABLE behavioral_signals (
                    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id      UUID NULL
                                 REFERENCES users(id) ON DELETE CASCADE,
                    -- No FK on listing_id: keep signals readable even after
                    -- a listing is deleted. Recommender already tolerates
                    -- dangling listing references.
                    listing_id   UUID NULL,
                    event_type   VARCHAR(32) NOT NULL,
                    -- event_type values (no DB enum to allow forward-compat):
                    --   fav_add | fav_remove | contact_tap | view |
                    --   details_tap | fav_add_stale | fav_add_orphan
                    source       VARCHAR(32) NOT NULL,
                    -- source values:
                    --   push_inline | in_app | bot_search | inline_mode
                    created_at   TIMESTAMP NOT NULL DEFAULT now()
                );
                CREATE INDEX idx_signals_user_created
                    ON behavioral_signals (user_id, created_at DESC)
                    WHERE user_id IS NOT NULL;
                CREATE INDEX idx_signals_listing_event
                    ON behavioral_signals (listing_id, event_type)
                    WHERE listing_id IS NOT NULL;
                CREATE INDEX idx_signals_created
                    ON behavioral_signals (created_at);
                COMMENT ON TABLE behavioral_signals IS
                    'Block D D2 — append-only personalization signal feed.'
                    ' Retain 180 days raw; recommender consumes weekly aggregates.';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS behavioral_signals CASCADE;")
