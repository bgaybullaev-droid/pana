"""PR-C — add notifications.source column.

Lets the API distinguish preferences-based notifications from
saved-search matches without relying on title-substring heuristics.

Additive, idempotent, safe on populated tables.

Revision ID: prc_notification_source
Revises: prb_saved_searches_schema
Create Date: 2026-04-25
"""

from alembic import op

revision = "prc_notification_source"
down_revision = "prb_saved_searches_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'notifications' AND column_name = 'source'
            ) THEN
                ALTER TABLE notifications ADD COLUMN source VARCHAR(32);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE notifications DROP COLUMN IF EXISTS source")
