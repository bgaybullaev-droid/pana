"""prs_promotions_banners — Block phase-2 promotions + banners.

Adds three promotion-window columns to ``listings`` (urgent badge +
notification priority window — boost columns already exist) and a new
``banners`` table for the home-page / listing-page banner placements.

Revision ID: prs_promotions_banners
Revises: prq_block_f_exports
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "prs_promotions_banners"
down_revision: str | None = "prq_block_f_exports"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    # ── 1. Promotion-window columns on listings ───────────────────────
    # (is_boosted / boost_until already exist per audit — only the new
    # urgent-badge + notify-priority windows are added here.)
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='listings' AND column_name='has_urgent_badge'
            ) THEN
                ALTER TABLE listings
                    ADD COLUMN has_urgent_badge BOOLEAN NOT NULL DEFAULT false,
                    ADD COLUMN urgent_until TIMESTAMP NULL,
                    ADD COLUMN notify_priority_until TIMESTAMP NULL;
            END IF;
        END $$;
        """
    )

    # ── 2. Banners table ─────────────────────────────────────────────
    op.create_table(
        "banners",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
        sa.Column("target_url", sa.String(500), nullable=False),
        # placement values: home_top | home_inline | listing_inline
        sa.Column("placement", sa.String(32), nullable=False),
        # language values: ru | uz | uz_cyrl | *
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "starts_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ends_at", sa.DateTime, nullable=True),
        sa.Column(
            "impressions",
            sa.BigInteger,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "clicks",
            sa.BigInteger,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        """
        CREATE INDEX ix_banners_active_placement_lang
            ON banners (placement, language)
            WHERE is_active;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_banners_active_placement_lang;")
    op.drop_table("banners")
    op.execute(
        """
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='listings' AND column_name='has_urgent_badge'
            ) THEN
                ALTER TABLE listings
                    DROP COLUMN has_urgent_badge,
                    DROP COLUMN urgent_until,
                    DROP COLUMN notify_priority_until;
            END IF;
        END $$;
        """
    )
