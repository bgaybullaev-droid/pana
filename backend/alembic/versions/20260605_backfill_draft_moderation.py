"""Backfill moderation_status=approved for manually-created active listings.

Listings created via the seller draft flow (POST /listings/draft → PATCH to
active) were published without auto-approval because the PATCH handler did not
set moderation_status=APPROVED when flipping DRAFT → ACTIVE.  The public feed
requires moderation_status=approved so those listings were invisible to buyers.

This migration approves every active listing that was created manually
(source_type='manual') and still has moderation_status='pending'.

Revision ID: backfill_draft_moderation
Revises: rename_city_district_keys
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa

revision = "backfill_draft_moderation"
down_revision = "rename_city_district_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE listings
            SET moderation_status = 'approved'
            WHERE status = 'active'
              AND moderation_status = 'pending'
              AND source_type = 'manual'
            """
        )
    )


def downgrade() -> None:
    # Not reversible — we cannot know which rows were pending vs approved
    # before this migration. No-op downgrade is intentional.
    pass
