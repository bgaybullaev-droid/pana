"""Add user_preferences table for feed personalization.

Revision ID: add_user_preferences
Revises: add_multilingual_columns
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "add_user_preferences"
down_revision = "add_multilingual_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("regions", ARRAY(sa.String), server_default="{}"),
        sa.Column("districts", ARRAY(sa.String), server_default="{}"),
        sa.Column("property_types", ARRAY(sa.String), server_default="{}"),
        sa.Column("listing_types", ARRAY(sa.String), server_default="{}"),
        sa.Column("price_min", sa.Integer, nullable=True),
        sa.Column("price_max", sa.Integer, nullable=True),
        sa.Column("rooms", ARRAY(sa.Integer), server_default="{}"),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_user_preferences_user_id", table_name="user_preferences")
    op.drop_table("user_preferences")
