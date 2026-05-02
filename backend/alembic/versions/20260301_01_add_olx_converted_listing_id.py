"""Add converted_listing_id to olx_listings for OLX claim feature.

Revision ID: add_olx_converted_listing_id
Revises: add_region_to_listings
Create Date: 2026-03-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "add_olx_converted_listing_id"
down_revision = "add_region_to_listings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add converted_listing_id column (FK to listings.id, ON DELETE SET NULL)
    op.add_column(
        "olx_listings",
        sa.Column(
            "converted_listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    # Regular index for lookups
    op.create_index(
        "ix_olx_listings_converted_listing_id",
        "olx_listings",
        ["converted_listing_id"],
    )
    # Unique partial index: each OLX listing can map to at most one platform listing
    op.execute(
        "CREATE UNIQUE INDEX uq_olx_converted_listing "
        "ON olx_listings (converted_listing_id) "
        "WHERE converted_listing_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_olx_converted_listing")
    op.drop_index("ix_olx_listings_converted_listing_id", table_name="olx_listings")
    op.drop_column("olx_listings", "converted_listing_id")
