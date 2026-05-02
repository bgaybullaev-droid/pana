"""Add auth_source column to users and update identifier constraint.

Revision ID: add_user_auth_source
Revises: add_contact_phone_indexes
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "add_user_auth_source"
down_revision = "add_contact_phone_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add auth_source to users
    op.add_column(
        "users",
        sa.Column("auth_source", sa.String(20), nullable=True),
    )

    # Backfill existing users as 'telegram'
    op.execute("UPDATE users SET auth_source = 'telegram' WHERE telegram_id IS NOT NULL")

    # Update at_least_one_identifier constraint to allow username-only users
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS at_least_one_identifier")
    op.execute(
        """
        ALTER TABLE users ADD CONSTRAINT at_least_one_identifier
        CHECK (
            telegram_id IS NOT NULL OR
            phone IS NOT NULL OR
            email IS NOT NULL OR
            username IS NOT NULL
        )
        """
    )


def downgrade() -> None:
    # Restore original constraint
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS at_least_one_identifier")
    op.execute(
        """
        ALTER TABLE users ADD CONSTRAINT at_least_one_identifier
        CHECK (
            telegram_id IS NOT NULL OR
            phone IS NOT NULL OR
            email IS NOT NULL
        )
        """
    )

    # Drop auth_source
    op.drop_column("users", "auth_source")
