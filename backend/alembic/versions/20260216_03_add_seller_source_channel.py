"""Add source_channel to sellers and index on telegram_listings.source_channel.

Revision ID: add_seller_source_channel
Revises: make_seller_phone_nullable
Create Date: 2026-02-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "add_seller_source_channel"
down_revision = "make_seller_phone_nullable"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add source_channel to sellers
    op.add_column(
        "sellers",
        sa.Column("source_channel", sa.String(200), nullable=True),
    )
    op.execute(
        "CREATE UNIQUE INDEX ix_sellers_source_channel "
        "ON sellers (source_channel) WHERE source_channel IS NOT NULL"
    )

    # Index on telegram_listings.source_channel for login lookup
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_telegram_listings_source_channel "
        "ON telegram_listings (source_channel)"
    )


def downgrade() -> None:
    # Drop telegram_listings index
    op.execute("DROP INDEX IF EXISTS ix_telegram_listings_source_channel")

    # Drop source_channel
    op.execute("DROP INDEX IF EXISTS ix_sellers_source_channel")
    op.drop_column("sellers", "source_channel")
