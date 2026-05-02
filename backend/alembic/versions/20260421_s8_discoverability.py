"""Sprint 8 — Discoverability + lifecycle (T-023, T-033, T-036).

Blueprint §1.2 Sprint 8:
    - listings.slug VARCHAR(255) UNIQUE NULL
    - T-033 lifecycle uses existing expires_at + deleted_at — no new cols.
    - T-036 analytics — open decision (§7 q10); skipped at DB level here,
      will land via external pipeline.

Indexes per §4.1 Sprint 8:
    - idx_listings_slug    UNIQUE WHERE slug IS NOT NULL AND deleted_at IS NULL
    - idx_listings_expires_at  WHERE status='EXPIRED' AND deleted_at IS NULL

Revision ID: s8_discoverability
Revises: s7_roles_media
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa

revision = "s8_discoverability"
down_revision = "s7_roles_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'listings' AND column_name = 'slug'
            ) THEN
                ALTER TABLE listings ADD COLUMN slug VARCHAR(255);
            END IF;
        END $$;
        """
    )

    op.create_index(
        "idx_listings_slug",
        "listings",
        ["slug"],
        unique=True,
        postgresql_where=sa.text("slug IS NOT NULL AND deleted_at IS NULL"),
    )
    op.create_index(
        "idx_listings_expires_at",
        "listings",
        ["expires_at"],
        postgresql_where=sa.text("status = 'EXPIRED' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_listings_expires_at", table_name="listings")
    op.drop_index("idx_listings_slug", table_name="listings")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS slug;")
