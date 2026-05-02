"""Add land_purpose column to listings, telegram_listings, and olx_listings.

Revision ID: add_land_purpose
Revises: add_building_type_condition
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "add_land_purpose"
down_revision = "add_building_type_condition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("land_purpose", sa.String(50), nullable=True))
    op.add_column("telegram_listings", sa.Column("land_purpose", sa.String(50), nullable=True))
    op.add_column("olx_listings", sa.Column("land_purpose", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("olx_listings", "land_purpose")
    op.drop_column("telegram_listings", "land_purpose")
    op.drop_column("listings", "land_purpose")
