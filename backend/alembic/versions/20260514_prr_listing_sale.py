"""prr_listing_sale — Phase-2 deal-status + analytics.

Adds the ``listing_sales`` table (one row per sold listing, the source
of truth for sale price/currency/timestamp/notes) and three redundant
denormalised columns on ``listings`` (``sold_price``, ``sold_currency``,
``sold_at``) for cheap feed-side filters that don't want to JOIN the
sales table.

Revision ID: prr_listing_sale
Revises: prq_block_f_exports
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "prr_listing_sale"
down_revision: str | None = "prq_block_f_exports"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "listing_sales",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "listing_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sold_price", sa.BigInteger, nullable=False),
        sa.Column("sold_currency", sa.String(8), nullable=False),
        sa.Column(
            "sold_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("listing_id", name="uq_listing_sales_listing_id"),
    )
    op.create_index(
        "ix_listing_sales_listing_id",
        "listing_sales",
        ["listing_id"],
    )
    op.create_index(
        "ix_listing_sales_sold_at",
        "listing_sales",
        ["sold_at"],
    )
    op.create_index(
        "ix_listing_sales_currency_sold_at",
        "listing_sales",
        ["sold_currency", "sold_at"],
    )

    # Denormalised mirror columns on listings — populated by the PATCH
    # handler at the moment of the SOLD transition. Cheap feed filters
    # ("sold under X in last 30 days") avoid the JOIN.
    op.add_column(
        "listings",
        sa.Column("sold_price", sa.BigInteger, nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("sold_currency", sa.String(8), nullable=True),
    )
    op.add_column(
        "listings",
        sa.Column("sold_at", sa.DateTime, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("listings", "sold_at")
    op.drop_column("listings", "sold_currency")
    op.drop_column("listings", "sold_price")
    op.drop_index("ix_listing_sales_currency_sold_at", table_name="listing_sales")
    op.drop_index("ix_listing_sales_sold_at", table_name="listing_sales")
    op.drop_index("ix_listing_sales_listing_id", table_name="listing_sales")
    op.drop_table("listing_sales")
