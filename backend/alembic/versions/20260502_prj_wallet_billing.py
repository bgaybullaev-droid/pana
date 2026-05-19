"""PR-J — Block C V2.0 (C3) — wallet, transaction, subscription tables.

Three new tables and five new enum types. Pure addition; no existing
tables are modified. All money columns are BIGINT in smallest currency
unit (UZS=whole, USD=cents) per decision-pass / MONEY_STORAGE_DECISION.

Tables created:
- ``wallets`` — one per user, lazy-created; BIGINT current_balance.
- ``transactions`` — append-mostly ledger; idempotency_key UNIQUE for
  webhook dedup; foreign-keyed to wallets (RESTRICT) and subscriptions
  (SET NULL on subscription delete).
- ``subscriptions`` — one per active billing relationship; object_id
  is polymorphic (no FK to listings).

Enum types:
- ``transaction_type``      ('deposit', 'withdrawal', 'refund', 'adjustment')
- ``transaction_status``    ('pending', 'completed', 'failed', 'refunded')
- ``subscription_type``     ('cabinet', 'listing_extra')
- ``subscription_status``   ('active', 'paused', 'cancelled', 'expired', 'grace')
- ``billing_cycle``         ('monthly', 'yearly')

Per Postgres-and-alembic precedent established in Block A (PR-G), enum
creation runs in autocommit so CREATE TYPE commits before any column
definition references the type.

Additive, idempotent. Tables empty on first deploy; wallet rows are
lazy-created by the service layer.

Revision ID: prj_wallet_billing
Revises: pri_source_metric_notified
Create Date: 2026-05-02
"""

from alembic import op

revision = "prj_wallet_billing"
down_revision = "pri_source_metric_notified"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── (1) Enum types — autocommit so the values are visible to later DDL
    with op.get_context().autocommit_block():
        op.execute(
            """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transaction_type') THEN
                    CREATE TYPE transaction_type AS ENUM (
                        'deposit', 'withdrawal', 'refund', 'adjustment'
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transaction_status') THEN
                    CREATE TYPE transaction_status AS ENUM (
                        'pending', 'completed', 'failed', 'refunded'
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscription_type') THEN
                    CREATE TYPE subscription_type AS ENUM (
                        'cabinet', 'listing_extra'
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscription_status') THEN
                    CREATE TYPE subscription_status AS ENUM (
                        'active', 'paused', 'cancelled', 'expired', 'grace'
                    );
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'billing_cycle') THEN
                    CREATE TYPE billing_cycle AS ENUM ('monthly', 'yearly');
                END IF;
            END $$;
            """
        )

    # ── (2) wallets — one per user
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                           WHERE table_name = 'wallets') THEN
                CREATE TABLE wallets (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id         UUID NOT NULL UNIQUE
                                    REFERENCES users(id) ON DELETE CASCADE,
                    current_balance BIGINT NOT NULL DEFAULT 0
                                    CHECK (current_balance >= 0),
                    currency        currency NOT NULL DEFAULT 'UZS',
                    version         INTEGER NOT NULL DEFAULT 0,
                    created_at      TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at      TIMESTAMP NOT NULL DEFAULT now()
                );
                CREATE INDEX idx_wallets_user_id ON wallets (user_id);
                COMMENT ON COLUMN wallets.current_balance IS
                    'Smallest currency unit. UZS: whole UZS. USD: cents.';
            END IF;
        END $$;
        """
    )

    # ── (3) subscriptions — created BEFORE transactions because transactions
    # has an FK to subscriptions (SET NULL).
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                           WHERE table_name = 'subscriptions') THEN
                CREATE TABLE subscriptions (
                    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id         UUID NOT NULL
                                    REFERENCES users(id) ON DELETE CASCADE,
                    type            subscription_type NOT NULL,
                    object_id       UUID NULL,
                    price           BIGINT NOT NULL CHECK (price >= 0),
                    currency        currency NOT NULL DEFAULT 'UZS',
                    billing_cycle   billing_cycle NOT NULL DEFAULT 'monthly',
                    status          subscription_status NOT NULL DEFAULT 'active',
                    starts_at       TIMESTAMP NOT NULL,
                    ends_at         TIMESTAMP NULL,
                    next_billing_at TIMESTAMP NULL,
                    created_at      TIMESTAMP NOT NULL DEFAULT now(),
                    updated_at      TIMESTAMP NOT NULL DEFAULT now()
                );
                CREATE INDEX idx_sub_user_type ON subscriptions (user_id, type);
                CREATE INDEX idx_sub_next_billing ON subscriptions (next_billing_at)
                    WHERE next_billing_at IS NOT NULL;
                COMMENT ON COLUMN subscriptions.price IS
                    'Smallest currency unit per billing cycle.';
            END IF;
        END $$;
        """
    )

    # ── (4) transactions
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                           WHERE table_name = 'transactions') THEN
                CREATE TABLE transactions (
                    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    wallet_id           UUID NOT NULL
                                        REFERENCES wallets(id) ON DELETE RESTRICT,
                    type                transaction_type NOT NULL,
                    amount              BIGINT NOT NULL CHECK (amount > 0),
                    currency            currency NOT NULL,
                    status              transaction_status NOT NULL DEFAULT 'pending',
                    external_payment_id VARCHAR(128) NULL,
                    subscription_id     UUID NULL
                                        REFERENCES subscriptions(id) ON DELETE SET NULL,
                    idempotency_key     VARCHAR(64) NULL UNIQUE,
                    transaction_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at          TIMESTAMP NOT NULL DEFAULT now(),
                    completed_at        TIMESTAMP NULL
                );
                CREATE INDEX idx_tx_wallet_status ON transactions (wallet_id, status);
                CREATE INDEX idx_tx_external_payment_id ON transactions
                    (external_payment_id) WHERE external_payment_id IS NOT NULL;
                CREATE INDEX idx_tx_created_at ON transactions (created_at);
                COMMENT ON COLUMN transactions.amount IS
                    'Smallest currency unit. Always > 0. CHECK enforces.';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Tables drop only if empty (production must roll back via empty-state).
    op.execute(
        """
        DROP TABLE IF EXISTS transactions CASCADE;
        DROP TABLE IF EXISTS subscriptions CASCADE;
        DROP TABLE IF EXISTS wallets CASCADE;
        """
    )
    # Enum types: drop only if no remaining dependents (defensive).
    op.execute(
        """
        DROP TYPE IF EXISTS transaction_type CASCADE;
        DROP TYPE IF EXISTS transaction_status CASCADE;
        DROP TYPE IF EXISTS subscription_type CASCADE;
        DROP TYPE IF EXISTS subscription_status CASCADE;
        DROP TYPE IF EXISTS billing_cycle CASCADE;
        """
    )
