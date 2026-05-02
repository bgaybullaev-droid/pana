"""Make Seller.phone nullable with partial unique index.

Revision ID: make_seller_phone_nullable
Revises: add_user_auth_source
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "make_seller_phone_nullable"
down_revision = "add_user_auth_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make Seller.phone nullable
    op.alter_column(
        "sellers",
        "phone",
        existing_type=sa.String(20),
        nullable=True,
    )

    # Replace unique constraint with partial unique index (allows multiple NULLs)
    op.execute("ALTER TABLE sellers DROP CONSTRAINT IF EXISTS sellers_phone_key")
    op.execute(
        "CREATE UNIQUE INDEX ix_sellers_phone_unique "
        "ON sellers (phone) WHERE phone IS NOT NULL"
    )


def downgrade() -> None:
    # Restore Seller.phone unique constraint
    op.execute("DROP INDEX IF EXISTS ix_sellers_phone_unique")
    op.execute(
        "ALTER TABLE sellers ADD CONSTRAINT sellers_phone_key UNIQUE (phone)"
    )
    op.alter_column(
        "sellers",
        "phone",
        existing_type=sa.String(20),
        nullable=False,
    )
