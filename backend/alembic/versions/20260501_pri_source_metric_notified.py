"""PR-I — Block A V2.0 (A8) — add ``notified`` counter to source_metric.

Tracks how many listings from each source resulted in a Telegram push
to a registered seller (CRAWLED_MATCH notification). Surfaces the A4
fanout efficacy per source on the admin dashboard.

Additive, idempotent.

Revision ID: pri_source_metric_notified
Revises: prh_source_metric_and_seed
Create Date: 2026-05-01
"""

from alembic import op

revision = "pri_source_metric_notified"
down_revision = "prh_source_metric_and_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'source_metric' AND column_name = 'notified'
            ) THEN
                ALTER TABLE source_metric
                    ADD COLUMN notified INTEGER NOT NULL DEFAULT 0;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE source_metric DROP COLUMN IF EXISTS notified;")
