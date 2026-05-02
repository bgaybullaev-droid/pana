"""Add functional indexes on contact_phone for seller panel phone matching.

Revision ID: add_contact_phone_indexes
Revises: add_multi_provider_auth
Create Date: 2026-02-14
"""
from alembic import op

# revision identifiers
revision = "add_contact_phone_indexes"
down_revision = "add_multi_provider_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX idx_olx_listings_phone_suffix "
        "ON olx_listings (RIGHT(contact_phone, 9)) "
        "WHERE contact_phone IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX idx_telegram_listings_phone_suffix "
        "ON telegram_listings (RIGHT(contact_phone, 9)) "
        "WHERE contact_phone IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_olx_listings_phone_suffix")
    op.execute("DROP INDEX IF EXISTS idx_telegram_listings_phone_suffix")
