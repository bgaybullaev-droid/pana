"""Add new notification types and disabled_types preference column.

Revision ID: add_notif_types_prefs
Revises: add_land_purpose
Create Date: 2026-04-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers
revision = "add_notif_types_prefs"
down_revision = "add_land_purpose"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new enum values to notificationtype
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'listing_approved'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'listing_rejected'")
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'new_comment'")

    # Add disabled_types column to notification_preferences for per-type opt-out
    op.add_column(
        "notification_preferences",
        sa.Column(
            "disabled_types", ARRAY(sa.String()), server_default="{}", nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_column("notification_preferences", "disabled_types")
    # Note: PostgreSQL doesn't support removing enum values easily
