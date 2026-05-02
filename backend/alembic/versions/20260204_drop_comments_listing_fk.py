"""Drop foreign key constraint on comments.listing_id to allow comments on crawler listings.

Revision ID: drop_comments_fk
Revises: 20260203_add_crawler_tables
Create Date: 2026-02-04
"""
from alembic import op

# revision identifiers
revision = "drop_comments_fk"
down_revision = "add_crawler_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the FK constraint so comments can reference any listing source
    op.drop_constraint(
        "comments_listing_id_fkey", "comments", type_="foreignkey"
    )


def downgrade() -> None:
    op.create_foreign_key(
        "comments_listing_id_fkey",
        "comments",
        "listings",
        ["listing_id"],
        ["id"],
        ondelete="CASCADE",
    )
