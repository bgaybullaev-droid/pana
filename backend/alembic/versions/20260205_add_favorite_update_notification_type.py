"""Add favorite_update to notificationtype enum.

Revision ID: add_favorite_update_type
Revises: drop_notifications_fk
Create Date: 2026-02-05
"""
from alembic import op

# revision identifiers
revision = "add_favorite_update_type"
down_revision = "drop_notifications_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the new enum value to the existing type
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'favorite_update'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values easily
    # The downgrade would require recreating the type and all dependent columns
    pass
