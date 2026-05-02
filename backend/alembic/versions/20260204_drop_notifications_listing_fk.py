"""Drop foreign key constraint on notifications.listing_id to allow notifications for crawler listings.

Revision ID: drop_notifications_fk
Revises: drop_favorites_fk
Create Date: 2026-02-04
"""
from alembic import op

# revision identifiers
revision = "drop_notifications_fk"
down_revision = "drop_favorites_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "notifications_listing_id_fkey", "notifications", type_="foreignkey"
    )


def downgrade() -> None:
    op.create_foreign_key(
        "notifications_listing_id_fkey",
        "notifications",
        "listings",
        ["listing_id"],
        ["id"],
        ondelete="CASCADE",
    )
