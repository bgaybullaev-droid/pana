"""Add comments and comment_likes tables

Revision ID: add_comments
Revises: add_admin_panel_fields
Create Date: 2026-01-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_comments'
down_revision: Union[str, None] = 'add_admin_panel_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create comments table
    op.create_table(
        'comments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('listing_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('listings.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('likes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('replies_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create indexes for comments
    op.create_index('idx_comments_listing_id', 'comments', ['listing_id'])
    op.create_index('idx_comments_user_id', 'comments', ['user_id'])
    op.create_index('idx_comments_parent_id', 'comments', ['parent_id'])
    op.create_index('idx_comments_listing_created', 'comments', ['listing_id', 'created_at'])

    # Create comment_likes table
    op.create_table(
        'comment_likes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('comment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('comments.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('comment_id', 'user_id', name='uq_comment_user_like'),
    )

    # Create indexes for comment_likes
    op.create_index('idx_comment_likes_comment_id', 'comment_likes', ['comment_id'])
    op.create_index('idx_comment_likes_user_id', 'comment_likes', ['user_id'])

    # Add comments_count column to listings table
    op.add_column('listings', sa.Column('comments_count', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove comments_count from listings
    op.drop_column('listings', 'comments_count')

    # Drop comment_likes table
    op.drop_index('idx_comment_likes_user_id', 'comment_likes')
    op.drop_index('idx_comment_likes_comment_id', 'comment_likes')
    op.drop_table('comment_likes')

    # Drop comments table
    op.drop_index('idx_comments_listing_created', 'comments')
    op.drop_index('idx_comments_parent_id', 'comments')
    op.drop_index('idx_comments_user_id', 'comments')
    op.drop_index('idx_comments_listing_id', 'comments')
    op.drop_table('comments')
