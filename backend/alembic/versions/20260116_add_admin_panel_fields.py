"""Add admin panel fields for user and listing approval

Revision ID: add_admin_panel_fields
Revises: 011036dfb572
Create Date: 2026-01-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_admin_panel_fields'
down_revision: Union[str, None] = '011036dfb572'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create UserApprovalStatus enum
    userapprovalstatus = postgresql.ENUM(
        'PENDING', 'APPROVED', 'REJECTED',
        name='userapprovalstatus',
        create_type=False
    )
    userapprovalstatus.create(op.get_bind(), checkfirst=True)

    # Add columns to users table
    op.add_column('users', sa.Column(
        'approval_status',
        sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='userapprovalstatus'),
        nullable=False,
        server_default='APPROVED'  # Existing users are approved by default
    ))
    op.add_column('users', sa.Column('approval_notes', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('approved_by', sa.UUID(), nullable=True))
    op.add_column('users', sa.Column('approved_at', sa.DateTime(), nullable=True))

    # Add foreign key constraint for approved_by
    op.create_foreign_key(
        'fk_users_approved_by',
        'users', 'users',
        ['approved_by'], ['id'],
        ondelete='SET NULL'
    )

    # Create index on approval_status
    op.create_index('idx_users_approval_status', 'users', ['approval_status'])

    # Add columns to listings table for moderation tracking
    op.add_column('listings', sa.Column('moderated_by', sa.UUID(), nullable=True))
    op.add_column('listings', sa.Column('moderated_at', sa.DateTime(), nullable=True))

    # Add foreign key constraint for moderated_by
    op.create_foreign_key(
        'fk_listings_moderated_by',
        'listings', 'users',
        ['moderated_by'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove columns from listings
    op.drop_constraint('fk_listings_moderated_by', 'listings', type_='foreignkey')
    op.drop_column('listings', 'moderated_at')
    op.drop_column('listings', 'moderated_by')

    # Remove columns from users
    op.drop_index('idx_users_approval_status', 'users')
    op.drop_constraint('fk_users_approved_by', 'users', type_='foreignkey')
    op.drop_column('users', 'approved_at')
    op.drop_column('users', 'approved_by')
    op.drop_column('users', 'approval_notes')
    op.drop_column('users', 'approval_status')

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS userapprovalstatus")
