"""Add Phase 2 listing fields: extended property details, utilities, amenities.

Revision ID: add_listing_phase2_fields
Revises: add_notif_types_prefs
Create Date: 2026-04-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = "add_listing_phase2_fields"
down_revision = "add_notif_types_prefs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("living_area", sa.Float(), nullable=True))
    op.add_column("listings", sa.Column("kitchen_area", sa.Float(), nullable=True))
    op.add_column("listings", sa.Column("land_area", sa.Float(), nullable=True))
    op.add_column("listings", sa.Column("house_type", sa.String(50), nullable=True))
    op.add_column(
        "listings",
        sa.Column("house_condition", ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("location_type", ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("water_supply", ARRAY(sa.String()), nullable=True),
    )
    op.add_column("listings", sa.Column("electricity", sa.String(50), nullable=True))
    op.add_column("listings", sa.Column("heating", ARRAY(sa.String()), nullable=True))
    op.add_column("listings", sa.Column("gas_supply", sa.String(50), nullable=True))
    op.add_column("listings", sa.Column("sewage", sa.String(50), nullable=True))
    op.add_column("listings", sa.Column("is_furnished", sa.Boolean(), nullable=True))
    op.add_column(
        "listings",
        sa.Column(
            "is_negotiable",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )
    op.add_column("listings", sa.Column("amenities", ARRAY(sa.String()), nullable=True))
    op.add_column(
        "listings",
        sa.Column("nearby_amenities", ARRAY(sa.String()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("listings", "nearby_amenities")
    op.drop_column("listings", "amenities")
    op.drop_column("listings", "is_negotiable")
    op.drop_column("listings", "is_furnished")
    op.drop_column("listings", "sewage")
    op.drop_column("listings", "gas_supply")
    op.drop_column("listings", "heating")
    op.drop_column("listings", "electricity")
    op.drop_column("listings", "water_supply")
    op.drop_column("listings", "location_type")
    op.drop_column("listings", "house_condition")
    op.drop_column("listings", "house_type")
    op.drop_column("listings", "land_area")
    op.drop_column("listings", "kitchen_area")
    op.drop_column("listings", "living_area")
