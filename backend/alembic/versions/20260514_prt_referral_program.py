"""PR-T — phase-2 referral program.

Adds the cabinet-side referral program: every user gets an opaque
8-char ``referral_code`` they can share via ``t.me/<bot>?start=ref_…``;
qualifying actions by the referred user emit reward rows. See
``app/services/referrals.py`` for the business logic.

Schema:
    users.referral_code             VARCHAR(12) NULL UNIQUE
        — 8-char Crockford alphabet, auto-generated lazily by the
          cabinet endpoint. UNIQUE so a regenerate operation can swap
          atomically.
    users.referred_by_user_id       (already exists — Block D D3)
    users.referral_source           (already exists — Block D D3)
    referral_events                 attribution ledger (signup/qualified/rewarded)
    referral_rewards                payouts to the referrer (links to wallet
                                    transactions when wallet.deposit succeeds)

Idempotency model:
    UNIQUE(referrer_user_id, referred_user_id, event_type) on
    ``referral_events`` is the source of truth — a duplicate
    "qualified" insert short-circuits via IntegrityError so a user
    can never be counted twice.

Revision ID: prt_referral_program
Revises: prq_block_f_exports
Create Date: 2026-05-14
"""

from __future__ import annotations

from alembic import op

# revision identifiers
revision: str = "prt_referral_program"
down_revision: str | None = "prq_block_f_exports"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # ── users.referral_code (and Block-D columns, defensively) ──────────
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='referral_code'
            ) THEN
                ALTER TABLE users
                    ADD COLUMN referral_code VARCHAR(12) NULL;
                CREATE UNIQUE INDEX uq_users_referral_code
                    ON users (referral_code)
                    WHERE referral_code IS NOT NULL;
            END IF;
            -- referred_by_user_id and referral_source are owned by Block D
            -- D3's earlier migration. The IF NOT EXISTS guards below let
            -- this migration run cleanly even if Block D was deferred.
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='referred_by_user_id'
            ) THEN
                ALTER TABLE users
                    ADD COLUMN referred_by_user_id UUID NULL
                        REFERENCES users(id) ON DELETE SET NULL;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='referral_source'
            ) THEN
                ALTER TABLE users
                    ADD COLUMN referral_source VARCHAR(64) NULL;
            END IF;
        END $$;
        """
    )

    # ── referral_events ────────────────────────────────────────────────
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'referral_events'
            ) THEN
                CREATE TABLE referral_events (
                    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    referrer_user_id  UUID NOT NULL
                                      REFERENCES users(id) ON DELETE CASCADE,
                    referred_user_id  UUID NOT NULL
                                      REFERENCES users(id) ON DELETE CASCADE,
                    event_type        VARCHAR(32) NOT NULL,
                    event_metadata    JSONB NULL,
                    created_at        TIMESTAMP NOT NULL DEFAULT now(),
                    CONSTRAINT uq_referral_event_triple
                        UNIQUE (referrer_user_id, referred_user_id, event_type)
                );
                CREATE INDEX idx_referral_events_referrer_created
                    ON referral_events (referrer_user_id, created_at DESC);
                COMMENT ON TABLE referral_events IS
                    'Phase-2 referral program — append-only attribution ledger.'
                    ' event_type in (signup, qualified, rewarded).';
            END IF;
        END $$;
        """
    )

    # ── referral_rewards ───────────────────────────────────────────────
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'referral_rewards'
            ) THEN
                CREATE TABLE referral_rewards (
                    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    referrer_user_id  UUID NOT NULL
                                      REFERENCES users(id) ON DELETE CASCADE,
                    amount_micros     BIGINT NOT NULL,
                    reason            VARCHAR(64) NOT NULL,
                    wallet_tx_id      UUID NULL
                                      REFERENCES transactions(id) ON DELETE SET NULL,
                    granted_at        TIMESTAMP NOT NULL DEFAULT now()
                );
                CREATE INDEX idx_referral_rewards_referrer_granted
                    ON referral_rewards (referrer_user_id, granted_at DESC);
                COMMENT ON TABLE referral_rewards IS
                    'Phase-2 referral program — payouts to referrers.'
                    ' wallet_tx_id NULL when wallet.deposit was unavailable;'
                    ' admins can backfill once wallet plumbing is in place.';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS referral_rewards CASCADE;")
    op.execute("DROP TABLE IF EXISTS referral_events CASCADE;")
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='users' AND column_name='referral_code'
            ) THEN
                DROP INDEX IF EXISTS uq_users_referral_code;
                ALTER TABLE users DROP COLUMN referral_code;
            END IF;
            -- referred_by_user_id / referral_source are owned by Block D —
            -- leave them in place.
        END $$;
        """
    )
