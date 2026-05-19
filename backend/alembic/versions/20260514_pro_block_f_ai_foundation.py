"""PR-F5a — Block F (F1 + F5 backbone) — AI generation foundation.

Three new tables plus one new column on ``listings`` and one new value
in the ``listingstatus`` enum.

- ``ai_generations`` — append-only log of every LLM call (success +
  failure outcomes). Retention 90 days, pruned by Celery beat task
  ``prune_ai_generations`` (PR-F5b).
- ``prompt_templates`` — DB-stored prompts with version + active flag.
  Worker reads the active row at task start; admin can iterate
  without redeploy. Partial unique index enforces ≤1 active per kind.
- ``ai_generation_feedback`` — seller-submitted "👎 не нравится" rows.
  Joined to ``ai_generations`` for context but FK ON DELETE SET NULL
  so feedback survives pruning of the generation.
- ``listings.last_ai_param_snapshot`` (JSONB) — captures the structured
  params at generation time so the cabinet Stage 2 can detect drift
  and offer a regenerate banner.
- ``listingstatus`` += ``'draft'`` — first-class status for the
  Stage 1 → Stage 2 publish flow. Wrapped in ``autocommit_block`` per
  Block A PR-G + Block C ``prj_wallet_billing`` precedent.

Retention strategy
==================
- ``ai_generations`` — 90 days. Pruning lives in
  ``app/workers/tasks/maintenance.py:prune_ai_generations``.
- ``ai_generation_feedback`` — retained indefinitely (small volume,
  high analytical value).
- ``prompt_templates`` — retained indefinitely. Old versions kept
  for rollback.

Estimated growth
================
- ~1K listings/day × 1.2 retries avg ⇒ ~1200 ``ai_generations``
  rows/day ⇒ ~110K rows/quarter ⇒ ~12 MB/quarter.
- ``ai_generation_feedback`` — ~5–10 rows/day at peak.
- ``prompt_templates`` — single-digit rows/year.

Revision ID: pro_block_f_ai_foundation
Revises: prn_autopost
Create Date: 2026-05-14
"""

from alembic import op


revision = "pro_block_f_ai_foundation"
down_revision = "prn_autopost"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── (1) Add 'DRAFT' to listingstatus enum.
    # Wrapped in autocommit_block so CREATE TYPE-like ops commit before
    # downstream DDL references the value (Block A PR-G precedent).
    #
    # The enum was created in initial_schema with UPPERCASE labels
    # ('ACTIVE', 'PAUSED', ...) — SQLAlchemy serialises ``enum.Enum``
    # members by ``.name`` (uppercase). The DRAFT label MUST match that
    # convention.
    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'listingstatus')
                      AND enumlabel = 'DRAFT'
                ) THEN
                    ALTER TYPE listingstatus ADD VALUE 'DRAFT';
                END IF;
            END $$;
            """
        )

    # ── (2) listings.last_ai_param_snapshot — JSONB nullable column.
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings'
                  AND column_name = 'last_ai_param_snapshot'
            ) THEN
                ALTER TABLE listings ADD COLUMN last_ai_param_snapshot JSONB NULL;
                COMMENT ON COLUMN listings.last_ai_param_snapshot IS
                    'Block F F1 — snapshot of structured params at AI generation time.'
                    ' Cabinet Stage 2 compares against current params to detect drift.';
            END IF;
        END $$;
        """
    )

    # ── (3) prompt_templates — DB-stored prompts with versioning.
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'prompt_templates'
            ) THEN
                CREATE TABLE prompt_templates (
                    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    kind                VARCHAR(48) NOT NULL,
                    version             INTEGER NOT NULL,
                    body                TEXT NOT NULL,
                    model_hint          VARCHAR(64) NULL,
                    is_active           BOOLEAN NOT NULL DEFAULT false,
                    notes               TEXT NULL,
                    created_by_user_id  UUID NULL REFERENCES users(id) ON DELETE SET NULL,
                    created_at          TIMESTAMP NOT NULL DEFAULT now()
                );
                -- Partial unique: at most one active prompt per kind.
                -- Makes activation a single-statement atomic swap.
                CREATE UNIQUE INDEX uq_prompt_templates_active_per_kind
                    ON prompt_templates (kind) WHERE is_active;
                CREATE INDEX idx_prompt_templates_kind_version
                    ON prompt_templates (kind, version DESC);
                COMMENT ON TABLE prompt_templates IS
                    'Block F F5 — versioned LLM prompts. Worker reads is_active=true row.'
                    ' Partial unique index ensures ≤1 active per kind.';
            END IF;
        END $$;
        """
    )

    # ── (4) ai_generations — append-only generation log.
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'ai_generations'
            ) THEN
                CREATE TABLE ai_generations (
                    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    listing_id          UUID NULL
                                        REFERENCES listings(id) ON DELETE SET NULL,
                    prompt_template_id  UUID NULL
                                        REFERENCES prompt_templates(id) ON DELETE SET NULL,
                    model               VARCHAR(64) NOT NULL,
                    prompt_text         TEXT NOT NULL,
                    response_text       TEXT NOT NULL,
                    duration_ms         INTEGER NOT NULL,
                    input_tokens        INTEGER NULL,
                    output_tokens       INTEGER NULL,
                    cost_usd_micros     BIGINT NULL,
                    triggered_by        VARCHAR(32) NOT NULL,
                    outcome             VARCHAR(32) NOT NULL,
                    created_at          TIMESTAMP NOT NULL DEFAULT now()
                );
                CREATE INDEX idx_ai_generations_listing_created
                    ON ai_generations (listing_id, created_at DESC);
                CREATE INDEX idx_ai_generations_outcome_created
                    ON ai_generations (outcome, created_at DESC)
                    WHERE outcome != 'ok';
                COMMENT ON TABLE ai_generations IS
                    'Block F F5 — every LLM call (success + failure).'
                    ' Retention 90 days via prune_ai_generations cron.';
                COMMENT ON COLUMN ai_generations.cost_usd_micros IS
                    'USD cost in micros ($0.000001 units) to avoid float.';
                COMMENT ON COLUMN ai_generations.triggered_by IS
                    'manual | auto_parser | param_change | manual_retry';
                COMMENT ON COLUMN ai_generations.outcome IS
                    'ok | fallback_template | timeout | rate_limit | invalid_response';
            END IF;
        END $$;
        """
    )

    # ── (5) ai_generation_feedback — seller "не нравится" rows.
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'ai_generation_feedback'
            ) THEN
                CREATE TABLE ai_generation_feedback (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    generation_id   UUID NULL
                                    REFERENCES ai_generations(id) ON DELETE SET NULL,
                    listing_id      UUID NULL
                                    REFERENCES listings(id) ON DELETE SET NULL,
                    user_id         UUID NOT NULL
                                    REFERENCES users(id) ON DELETE CASCADE,
                    category        VARCHAR(32) NOT NULL,
                    comment         TEXT NULL,
                    handled         BOOLEAN NOT NULL DEFAULT false,
                    created_at      TIMESTAMP NOT NULL DEFAULT now()
                );
                CREATE INDEX idx_ai_feedback_handled_created
                    ON ai_generation_feedback (handled, created_at DESC);
                COMMENT ON TABLE ai_generation_feedback IS
                    'Block F F5 — seller-submitted feedback on AI text.'
                    ' Retained indefinitely.';
                COMMENT ON COLUMN ai_generation_feedback.category IS
                    'grammar | unnatural | factual | too_long | too_short | other';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Drop in reverse FK order. Enum value 'draft' is PG-irreversible —
    # left as harmless residual (no rows reference it after table drop).
    op.execute("DROP TABLE IF EXISTS ai_generation_feedback CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_generations CASCADE;")
    op.execute("DROP TABLE IF EXISTS prompt_templates CASCADE;")
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings'
                  AND column_name = 'last_ai_param_snapshot'
            ) THEN
                ALTER TABLE listings DROP COLUMN last_ai_param_snapshot;
            END IF;
        END $$;
        """
    )
