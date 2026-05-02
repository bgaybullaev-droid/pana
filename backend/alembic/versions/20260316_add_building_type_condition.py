"""Add building_type and condition columns to listings and telegram_listings.

Revision ID: add_building_type_condition
Revises: add_user_preferences
Create Date: 2026-03-16
"""
from alembic import op
import sqlalchemy as sa

revision = "add_building_type_condition"
down_revision = "add_user_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("building_type", sa.String(50), nullable=True))
    op.add_column("listings", sa.Column("condition", sa.String(50), nullable=True))
    op.add_column("telegram_listings", sa.Column("building_type", sa.String(50), nullable=True))
    op.add_column("telegram_listings", sa.Column("condition", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("telegram_listings", "condition")
    op.drop_column("telegram_listings", "building_type")
    op.drop_column("listings", "condition")
    op.drop_column("listings", "building_type")
