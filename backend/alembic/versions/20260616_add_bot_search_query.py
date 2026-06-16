"""Block D (FU5) — bot search-query telemetry.

Creates ``bot_search_queries``: an append-only capture of every executed
bot in-chat / Inline-Mode search. It feeds parser-dictionary iteration
(top unrecognized ``raw_text``) and the rule-based → LLM decision
(DECISION_MATRIX: revisit at >10% miss rate over a month).

``extracted_fields`` is a JSONB array of the parsed field names (empty
``[]`` ⇒ nothing recognized — the headline miss signal). 90-day
retention is handled by the ``prune_bot_search_queries`` Celery cron, so
this migration only creates the table + the ``created_at`` index the
prune job rides.

Idempotent: ``CREATE TABLE / INDEX IF NOT EXISTS`` so re-runs are safe.

Revision ID: bot_search_query
Revises: bot_rate_limit_settings
Create Date: 2026-06-16
"""

from alembic import op

revision = "bot_search_query"
down_revision = "bot_rate_limit_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bot_search_queries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_telegram_id BIGINT NULL,
            source VARCHAR(8) NOT NULL,
            raw_text VARCHAR(200) NOT NULL,
            extracted_fields JSONB NOT NULL DEFAULT '[]'::jsonb,
            results_count INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_bot_search_queries_created_at "
        "ON bot_search_queries (created_at);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bot_search_queries;")
