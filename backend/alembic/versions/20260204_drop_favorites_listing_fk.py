"""Drop foreign key constraint on favorites.listing_id to allow favorites on crawler listings.

Revision ID: drop_favorites_fk
Revises: drop_comments_fk
Create Date: 2026-02-04
"""
from alembic import op

# revision identifiers
revision = "drop_favorites_fk"
down_revision = "drop_comments_fk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "favorites_listing_id_fkey", "favorites", type_="foreignkey"
    )


def downgrade() -> None:
    op.create_foreign_key(
        "favorites_listing_id_fkey",
        "favorites",
        "listings",
        ["listing_id"],
        ["id"],
        ondelete="CASCADE",
    )
