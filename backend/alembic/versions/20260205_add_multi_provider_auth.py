"""Add multi-provider authentication fields to users table.

Revision ID: add_multi_provider_auth
Revises: add_favorite_update_type
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "add_multi_provider_auth"
down_revision = "add_favorite_update_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns for multi-provider auth
    op.add_column(
        "users",
        sa.Column("email", sa.String(200), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("phone_verified", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("google_id", sa.String(100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "auth_providers",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.add_column(
        "users",
        sa.Column("primary_auth_provider", sa.String(20), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_login_provider", sa.String(20), nullable=True),
    )

    # Make telegram_id nullable (users can now register via phone or Google)
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Create unique indexes for new identifier fields
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "ix_users_google_id",
        "users",
        ["google_id"],
        unique=True,
        postgresql_where=sa.text("google_id IS NOT NULL"),
    )

    # Update existing users to have 'telegram' in auth_providers
    op.execute(
        "UPDATE users SET auth_providers = ARRAY['telegram'], primary_auth_provider = 'telegram' "
        "WHERE telegram_id IS NOT NULL"
    )

    # Add check constraint: at least one identifier must exist
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


def downgrade() -> None:
    # Remove check constraint
    op.execute("ALTER TABLE users DROP CONSTRAINT IF EXISTS at_least_one_identifier")

    # Drop indexes
    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")

    # Make telegram_id NOT NULL again (will fail if there are users without telegram_id)
    op.alter_column(
        "users",
        "telegram_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Drop new columns
    op.drop_column("users", "last_login_provider")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "primary_auth_provider")
    op.drop_column("users", "auth_providers")
    op.drop_column("users", "google_id")
    op.drop_column("users", "phone_verified")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "email")
