"""PR-K2 — align billing enum type names with SQLAlchemy convention.

Block C V2.0 (C3) hotfix: the prj_wallet_billing migration created
enums as ``transaction_type`` etc. (snake_case), but SQLAlchemy's
``Enum(TransactionType, ...)`` derives the type name as
``transactiontype`` (lowercase, no underscore) — matching the existing
codebase convention (``listingstatus``, ``notificationtype``,
``currency``).

This migration renames the five new types so SQLAlchemy can resolve
them at runtime.

Revision ID: prk2_align_billing_enum_names
Revises: prk_user_phone
Create Date: 2026-05-04
"""

from alembic import op

revision = "prk2_align_billing_enum_names"
down_revision = "prk_user_phone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transaction_type') THEN
                ALTER TYPE transaction_type RENAME TO transactiontype;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transaction_status') THEN
                ALTER TYPE transaction_status RENAME TO transactionstatus;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscription_type') THEN
                ALTER TYPE subscription_type RENAME TO subscriptiontype;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscription_status') THEN
                ALTER TYPE subscription_status RENAME TO subscriptionstatus;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'billing_cycle') THEN
                ALTER TYPE billing_cycle RENAME TO billingcycle;
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transactiontype') THEN
                ALTER TYPE transactiontype RENAME TO transaction_type;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transactionstatus') THEN
                ALTER TYPE transactionstatus RENAME TO transaction_status;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscriptiontype') THEN
                ALTER TYPE subscriptiontype RENAME TO subscription_type;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'subscriptionstatus') THEN
                ALTER TYPE subscriptionstatus RENAME TO subscription_status;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'billingcycle') THEN
                ALTER TYPE billingcycle RENAME TO billing_cycle;
            END IF;
        END $$;
        """
    )
