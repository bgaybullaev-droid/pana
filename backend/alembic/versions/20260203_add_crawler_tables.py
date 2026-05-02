"""Add telegram_listings and olx_listings tables for crawler integration

Revision ID: add_crawler_tables
Revises: sync_comments_count
Create Date: 2026-02-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_crawler_tables'
down_revision: Union[str, None] = 'sync_comments_count'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- telegram_listings table ---
    op.create_table(
        'telegram_listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('property_type', sa.String(50), nullable=False),
        sa.Column('listing_type', sa.String(50), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False),
        sa.Column('rooms', sa.Integer(), nullable=True),
        sa.Column('area_sqm', sa.Float(), nullable=True),
        sa.Column('floor', sa.Integer(), nullable=True),
        sa.Column('total_floors', sa.Integer(), nullable=True),
        sa.Column('district', sa.String(100), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('amenities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('source_channel', sa.String(200), nullable=True),
        sa.Column('message_id', sa.Integer(), nullable=True),
        sa.Column('signature_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_telegram_listings_signature_hash', 'telegram_listings', ['signature_hash'])
    op.create_index('idx_telegram_listings_created_at', 'telegram_listings', ['created_at'])
    op.create_index('idx_telegram_listings_district', 'telegram_listings', ['district'])
    op.create_index('idx_telegram_listings_price', 'telegram_listings', ['price'])

    # --- olx_listings table ---
    op.create_table(
        'olx_listings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('olx_id', sa.String(50), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('property_type', sa.String(50), nullable=False),
        sa.Column('listing_type', sa.String(50), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False),
        sa.Column('rooms', sa.Integer(), nullable=True),
        sa.Column('area_sqm', sa.Float(), nullable=True),
        sa.Column('floor', sa.Integer(), nullable=True),
        sa.Column('total_floors', sa.Integer(), nullable=True),
        sa.Column('district', sa.String(100), nullable=True),
        sa.Column('address', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('amenities', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('contact_phone', sa.String(20), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('crawled_at', sa.DateTime(), nullable=False),
        sa.Column('seller_type', sa.String(20), nullable=True),
        sa.Column('seller_name', sa.String(200), nullable=True),
        sa.Column('views_count', sa.Integer(), nullable=True),
        sa.Column('posted_date', sa.String(100), nullable=True),
        sa.Column('building_type', sa.String(100), nullable=True),
        sa.Column('condition', sa.String(100), nullable=True),
        sa.Column('furnishing', sa.String(100), nullable=True),
        sa.Column('ceiling_height', sa.Float(), nullable=True),
        sa.Column('bathroom', sa.String(100), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('signature_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('olx_id'),
    )
    op.create_index('idx_olx_listings_olx_id', 'olx_listings', ['olx_id'])
    op.create_index('idx_olx_listings_signature_hash', 'olx_listings', ['signature_hash'])
    op.create_index('idx_olx_listings_created_at', 'olx_listings', ['created_at'])
    op.create_index('idx_olx_listings_district', 'olx_listings', ['district'])
    op.create_index('idx_olx_listings_price', 'olx_listings', ['price'])


def downgrade() -> None:
    op.drop_index('idx_olx_listings_price', table_name='olx_listings')
    op.drop_index('idx_olx_listings_district', table_name='olx_listings')
    op.drop_index('idx_olx_listings_created_at', table_name='olx_listings')
    op.drop_index('idx_olx_listings_signature_hash', table_name='olx_listings')
    op.drop_index('idx_olx_listings_olx_id', table_name='olx_listings')
    op.drop_table('olx_listings')

    op.drop_index('idx_telegram_listings_price', table_name='telegram_listings')
    op.drop_index('idx_telegram_listings_district', table_name='telegram_listings')
    op.drop_index('idx_telegram_listings_created_at', table_name='telegram_listings')
    op.drop_index('idx_telegram_listings_signature_hash', table_name='telegram_listings')
    op.drop_table('telegram_listings')
