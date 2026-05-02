"""PR-B — extend saved_searches for HTTP CRUD + new_count computation.

Adds the columns the frontend contract requires (see docs/system-blueprint.md
§5.1 + §9):

    query       VARCHAR(200)?  — optional free-text portion of the saved search
    sort        VARCHAR(30)    — serialized sort order, default 'relevance'

Also renames `last_run_at` → `last_seen_at` so the column expresses the
user-facing semantics ("when did the user last review this saved search
badge?") instead of the internal matcher run timestamp.

Non-destructive: `ALTER TABLE RENAME COLUMN` preserves data. The new
columns default-safe on existing rows.

Revision ID: prb_saved_searches_schema
Revises: pra_notification_settings
Create Date: 2026-04-24
"""

from alembic import op

revision = "prb_saved_searches_schema"
down_revision = "pra_notification_settings"
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


def _rename_col_if_source_exists(table: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = '{old}'
            ) AND NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = '{new}'
            ) THEN
                ALTER TABLE {table} RENAME COLUMN {old} TO {new};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    _add_col_if_missing("saved_searches", "query", "VARCHAR(200)")
    _add_col_if_missing(
        "saved_searches",
        "sort",
        "VARCHAR(30) NOT NULL DEFAULT 'relevance'",
    )
    _rename_col_if_source_exists("saved_searches", "last_run_at", "last_seen_at")

    # Defensive: if the column was never created (fresh install), add it.
    _add_col_if_missing("saved_searches", "last_seen_at", "TIMESTAMP")

    # Seed `last_seen_at` to `created_at` for rows that pre-date the rename.
    op.execute(
        "UPDATE saved_searches "
        "SET last_seen_at = created_at "
        "WHERE last_seen_at IS NULL;"
    )

    # Index to speed up per-user list queries.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_saved_searches_user_id "
        "ON saved_searches (user_id);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_saved_searches_user_id;")
    _rename_col_if_source_exists("saved_searches", "last_seen_at", "last_run_at")
    op.execute("ALTER TABLE saved_searches DROP COLUMN IF EXISTS sort;")
    op.execute("ALTER TABLE saved_searches DROP COLUMN IF EXISTS query;")
