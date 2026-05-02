"""Add notifications table for in-app notifications

Revision ID: add_notifications
Revises: add_comments
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_notifications'
down_revision: Union[str, None] = 'add_comments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if notification type enum already exists
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationtype')"
    ))
    enum_exists = result.scalar()

    if not enum_exists:
        # Create notification type enum using raw SQL
        op.execute(
            "CREATE TYPE notificationtype AS ENUM "
            "('comment_reply', 'price_drop', 'new_listing', 'favorite_update')"
        )

    # Check if notifications table exists
    result = conn.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'notifications')"
    ))
    table_exists = result.scalar()

    if not table_exists:
        # Create notifications table using raw SQL to avoid SQLAlchemy trying to create enum
        op.execute("""
            CREATE TABLE notifications (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type notificationtype NOT NULL,
                title VARCHAR(200) NOT NULL,
                message TEXT NOT NULL,
                listing_id UUID REFERENCES listings(id) ON DELETE CASCADE,
                comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
                actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
                read BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """)

        # Create indexes for notifications
        op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])
        op.create_index('idx_notifications_created_at', 'notifications', ['created_at'])
        op.execute(
            "CREATE INDEX idx_notifications_user_unread ON notifications (user_id, read) "
            "WHERE read = false"
        )


def downgrade() -> None:
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_notifications_user_unread")
    op.execute("DROP INDEX IF EXISTS idx_notifications_created_at")
    op.execute("DROP INDEX IF EXISTS idx_notifications_user_id")

    # Drop notifications table
    op.execute("DROP TABLE IF EXISTS notifications")

    # Drop notification type enum
    op.execute("DROP TYPE IF EXISTS notificationtype")
