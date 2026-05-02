"""PR-A — extend notification_preferences with delivery-budget fields.

Adds the frontend-facing columns that `GET/PUT /api/v1/notification-settings`
serves (see docs/system-blueprint.md §10 Option A):

    time_windows            TEXT[]   default {'morning','afternoon','evening'}
    source_saved_searches   BOOLEAN  default TRUE
    source_seller_follows   BOOLEAN  default TRUE
    source_ai_recs          BOOLEAN  default TRUE
    paused                  BOOLEAN  default FALSE

Additive migration — non-destructive, safe on populated tables. The
existing filter-preset columns (districts, property_types, …) stay
untouched and continue to back `/notifications/preferences`.

Revision ID: pra_notification_settings
Revises: s9_polish_marker
Create Date: 2026-04-23
"""

from alembic import op

revision = "pra_notification_settings"
down_revision = "s9_polish_marker"
branch_labels = None
depends_on = None


def _add_col_if_missing(table: str, column: str, ddl: str) -> None:
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
    _add_col_if_missing(
        "notification_preferences",
        "time_windows",
        "VARCHAR(20)[] NOT NULL DEFAULT ARRAY['morning','afternoon','evening']::VARCHAR(20)[]",
    )
    _add_col_if_missing(
        "notification_preferences",
        "source_saved_searches",
        "BOOLEAN NOT NULL DEFAULT TRUE",
    )
    _add_col_if_missing(
        "notification_preferences",
        "source_seller_follows",
        "BOOLEAN NOT NULL DEFAULT TRUE",
    )
    _add_col_if_missing(
        "notification_preferences",
        "source_ai_recs",
        "BOOLEAN NOT NULL DEFAULT TRUE",
    )
    _add_col_if_missing(
        "notification_preferences",
        "paused",
        "BOOLEAN NOT NULL DEFAULT FALSE",
    )

    # CHECK: time_windows elements must be in the allowlist.
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_notification_prefs_time_windows'
            ) THEN
                ALTER TABLE notification_preferences
                    ADD CONSTRAINT ck_notification_prefs_time_windows
                    CHECK (
                        time_windows <@ ARRAY['morning','afternoon','evening']::VARCHAR(20)[]
                    );
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE notification_preferences "
        "DROP CONSTRAINT IF EXISTS ck_notification_prefs_time_windows;"
    )
    for col in (
        "paused",
        "source_ai_recs",
        "source_seller_follows",
        "source_saved_searches",
        "time_windows",
    ):
        op.execute(f"ALTER TABLE notification_preferences DROP COLUMN IF EXISTS {col};")
