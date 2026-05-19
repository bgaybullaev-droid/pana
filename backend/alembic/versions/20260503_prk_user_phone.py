"""PR-K — Block C V2.0 (C4) — user_phones + phone_verify_attempt.

Two new tables and a backfill from ``users.phone`` so every existing
user has a row in ``user_phones`` with ``is_primary=true``.

Per decision-pass / PHONE_IDENTITY_MODEL.md §11:
- ``user_phones`` table: globally-unique phone, partial-unique primary
  per user.
- ``phone_verify_attempt`` log table is folded in here as forward-compat
  for C5's signal detection (avoids a separate trivial migration later).

Backfill is idempotent: ``ON CONFLICT (phone) DO NOTHING`` handles
the (impossible-by-canonicalize-migration) edge case where two users
somehow share a phone.

Additive, idempotent. No existing tables modified.

Revision ID: prk_user_phone
Revises: prj_wallet_billing
Create Date: 2026-05-03
"""

from alembic import op

revision = "prk_user_phone"
down_revision = "prj_wallet_billing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── (1) user_phones table
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                           WHERE table_name = 'user_phones') THEN
                CREATE TABLE user_phones (
                    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id             UUID NOT NULL
                                        REFERENCES users(id) ON DELETE CASCADE,
                    phone               VARCHAR(20) NOT NULL,
                    is_primary          BOOLEAN NOT NULL DEFAULT false,
                    verification_method VARCHAR(16) NOT NULL,
                    verified_at         TIMESTAMP NOT NULL,
                    created_at          TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at          TIMESTAMP NOT NULL DEFAULT now()
                );

                -- Globally unique phone — one phone, one owner.
                CREATE UNIQUE INDEX uq_user_phones_phone
                    ON user_phones (phone);

                -- Partial unique: exactly one primary per user.
                CREATE UNIQUE INDEX uq_user_phones_primary
                    ON user_phones (user_id)
                    WHERE is_primary = true;

                CREATE INDEX idx_user_phones_user
                    ON user_phones (user_id);
            END IF;
        END $$;
        """
    )

    # ── (2) Backfill — every user with a non-null phone gets a primary row.
    # Idempotent via ON CONFLICT (phone). Re-running is safe: existing
    # rows are preserved; only missing ones inserted.
    op.execute(
        """
        INSERT INTO user_phones (
            user_id, phone, is_primary, verification_method, verified_at
        )
        SELECT
            id,
            phone,
            true,
            'legacy',
            COALESCE(last_login_at, created_at, now())
        FROM users
        WHERE phone IS NOT NULL
        ON CONFLICT (phone) DO NOTHING;
        """
    )

    # ── (3) phone_verify_attempt log (forward-compat for C5)
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                           WHERE table_name = 'phone_verify_attempt') THEN
                CREATE TABLE phone_verify_attempt (
                    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id     UUID NOT NULL
                                REFERENCES users(id) ON DELETE CASCADE,
                    phone       VARCHAR(20) NOT NULL,
                    succeeded   BOOLEAN NOT NULL DEFAULT false,
                    created_at  TIMESTAMP NOT NULL DEFAULT now()
                );
                CREATE INDEX idx_phone_verify_attempt_user
                    ON phone_verify_attempt (user_id);
                CREATE INDEX idx_phone_verify_attempt_phone_time
                    ON phone_verify_attempt (phone, created_at DESC);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP TABLE IF EXISTS phone_verify_attempt CASCADE;
        DROP TABLE IF EXISTS user_phones CASCADE;
        """
    )
