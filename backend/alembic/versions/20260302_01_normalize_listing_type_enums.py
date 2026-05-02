"""Normalize listing_type and property_type values in crawled tables.

Fixes: sale → sell, daily_rent → rent, office → commercial
to match backend ListingType / PropertyType enums.

Revision ID: normalize_listing_type_enums
Revises: add_olx_converted_listing_id
"""

from alembic import op

revision = "normalize_listing_type_enums"
down_revision = "add_olx_converted_listing_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # listing_type: sale → sell
    op.execute("UPDATE telegram_listings SET listing_type = 'sell' WHERE listing_type = 'sale'")
    op.execute("UPDATE olx_listings SET listing_type = 'sell' WHERE listing_type = 'sale'")

    # listing_type: daily_rent → rent
    op.execute("UPDATE olx_listings SET listing_type = 'rent' WHERE listing_type = 'daily_rent'")

    # property_type: office → commercial
    op.execute("UPDATE olx_listings SET property_type = 'commercial' WHERE property_type = 'office'")


def downgrade() -> None:
    # Reverse: sell → sale
    op.execute("UPDATE telegram_listings SET listing_type = 'sale' WHERE listing_type = 'sell'")
    op.execute("UPDATE olx_listings SET listing_type = 'sale' WHERE listing_type = 'sell'")

    # daily_rent cannot be distinguished from rent after merge, skip
    # office cannot be distinguished from commercial after merge, skip
