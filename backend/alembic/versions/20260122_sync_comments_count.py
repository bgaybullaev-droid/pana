"""Sync comments_count with actual comment counts

Revision ID: sync_comments_count
Revises: add_notifications
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'sync_comments_count'
down_revision: Union[str, None] = 'add_notifications'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sync comments_count with actual count of top-level comments
    # This updates all listings to have the correct comments_count
    op.execute("""
        UPDATE listings
        SET comments_count = (
            SELECT COUNT(*)
            FROM comments
            WHERE comments.listing_id = listings.id
        )
    """)


def downgrade() -> None:
    # Reset comments_count to 0 (revert to initial state)
    op.execute("UPDATE listings SET comments_count = 0")
