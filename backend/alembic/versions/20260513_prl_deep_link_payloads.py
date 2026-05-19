"""PR-D3a — Block D V2.0 (D3) — deep-link payload tables.

Three new tables plus two new columns on ``users``:

- ``deep_link_payloads`` — short-id index of stored payload JSON.
  MVP body is filter-state for marketing share links; the ``kind``
  discriminator keeps the table reusable.
- ``claim_invites`` — single-use, expiring B2B onboarding tickets.
  Authoritative row for the security model (see security model in
  DECISION_MATRIX D3-Q2); the payload value alone is not trusted.
- ``deep_link_events`` — append-only audit log of every ``/start
  <payload>`` entry (and Mini App ``startapp`` entry) regardless of
  payload validity. Powers abuse analysis and campaign attribution.

User columns added:
- ``referred_by_user_id`` — nullable self-FK. Written only on
  first-time user registration (D3-Q3 — no retroactive attribution).
- ``referral_source`` — free-text bucket ("ad_yandex", "blogger_x").

All additions are purely additive — no destructive DDL, no existing
table or row touched.

Revision ID: prl_deep_link_payloads
Revises: prk2_align_billing_enum_names
Create Date: 2026-05-13
"""

from alembic import op

revision = "prl_deep_link_payloads"
down_revision = "prk2_align_billing_enum_names"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── (1) users — referral tracking columns
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name = 'referred_by_user_id'
            ) THEN
                ALTER TABLE users
                    ADD COLUMN referred_by_user_id UUID
                    REFERENCES users(id) ON DELETE SET NULL;
                CREATE INDEX idx_users_referred_by_user_id
                    ON users (referred_by_user_id)
                    WHERE referred_by_user_id IS NOT NULL;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users'
                  AND column_name = 'referral_source'
            ) THEN
                ALTER TABLE users
                    ADD COLUMN referral_source VARCHAR(64);
            END IF;
        END $$;
        """
    )

    # ── (2) deep_link_payloads — short-id → JSON payload
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'deep_link_payloads'
            ) THEN
                CREATE TABLE deep_link_payloads (
                    id                  VARCHAR(12) PRIMARY KEY,
                    kind                VARCHAR(16) NOT NULL,
                    payload             JSONB NOT NULL,
                    created_by_user_id  UUID NULL
                                        REFERENCES users(id) ON DELETE SET NULL,
                    created_at          TIMESTAMP NOT NULL DEFAULT now(),
                    used_count          INTEGER NOT NULL DEFAULT 0
                );
                CREATE INDEX idx_dlp_kind_created
                    ON deep_link_payloads (kind, created_at DESC);
                CREATE INDEX idx_dlp_created_by
                    ON deep_link_payloads (created_by_user_id)
                    WHERE created_by_user_id IS NOT NULL;
                COMMENT ON TABLE deep_link_payloads IS
                    'Block D D3 — short-id indirection table for deep-link payloads.'
                    ' MVP kind="filter". Rows never expire (D3-Q4).';
            END IF;
        END $$;
        """
    )

    # ── (3) claim_invites — single-use, expiring B2B tickets
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'claim_invites'
            ) THEN
                CREATE TABLE claim_invites (
                    id                      VARCHAR(12) PRIMARY KEY,
                    kind                    VARCHAR(16) NOT NULL,
                    pre_imported_user_id    UUID NULL
                                            REFERENCES users(id) ON DELETE SET NULL,
                    channel_username        VARCHAR(64) NULL,
                    expires_at              TIMESTAMP NOT NULL,
                    used_at                 TIMESTAMP NULL,
                    used_by_telegram_id     BIGINT NULL,
                    created_at              TIMESTAMP NOT NULL DEFAULT now(),
                    CONSTRAINT chk_claim_invites_kind CHECK (kind IN ('claim', 'agent')),
                    CONSTRAINT chk_claim_invites_target CHECK (
                        (kind = 'claim' AND pre_imported_user_id IS NOT NULL)
                        OR (kind = 'agent' AND channel_username IS NOT NULL)
                    )
                );
                CREATE INDEX idx_claim_invites_pre_imported
                    ON claim_invites (pre_imported_user_id)
                    WHERE pre_imported_user_id IS NOT NULL;
                CREATE INDEX idx_claim_invites_channel
                    ON claim_invites (channel_username)
                    WHERE channel_username IS NOT NULL;
                CREATE INDEX idx_claim_invites_expires
                    ON claim_invites (expires_at)
                    WHERE used_at IS NULL;
                COMMENT ON TABLE claim_invites IS
                    'Block D D3 — single-use, expiring B2B onboarding tickets.'
                    ' Row presence + unused state is the auth check;'
                    ' the URL payload alone is never trusted.';
            END IF;
        END $$;
        """
    )

    # ── (4) deep_link_events — append-only audit + analytics log
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'deep_link_events'
            ) THEN
                CREATE TABLE deep_link_events (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    prefix          VARCHAR(16) NOT NULL,
                    payload         VARCHAR(64) NOT NULL,
                    user_id         UUID NULL
                                    REFERENCES users(id) ON DELETE SET NULL,
                    is_new_user     BOOLEAN NOT NULL DEFAULT false,
                    outcome         VARCHAR(24) NOT NULL DEFAULT 'open',
                    created_at      TIMESTAMP NOT NULL DEFAULT now()
                );
                CREATE INDEX idx_dle_prefix_created
                    ON deep_link_events (prefix, created_at DESC);
                CREATE INDEX idx_dle_user_created
                    ON deep_link_events (user_id, created_at DESC)
                    WHERE user_id IS NOT NULL;
                COMMENT ON COLUMN deep_link_events.outcome IS
                    'open | resolved | rejected_unknown | rejected_expired |'
                    ' rejected_consumed | rejected_mismatch';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Drop in reverse-FK order. Tables drop only when empty in production
    # — caller must clear rows manually before invoking downgrade.
    op.execute("DROP TABLE IF EXISTS deep_link_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS claim_invites CASCADE;")
    op.execute("DROP TABLE IF EXISTS deep_link_payloads CASCADE;")
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'referred_by_user_id'
            ) THEN
                ALTER TABLE users DROP COLUMN referred_by_user_id;
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'referral_source'
            ) THEN
                ALTER TABLE users DROP COLUMN referral_source;
            END IF;
        END $$;
        """
    )
