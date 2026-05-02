"""Sprint 7 — Roles, moderation, media (T-027, T-028, T-035).

Blueprint §1.2 Sprint 7:
    - sellers.is_developer_verified BOOLEAN NOT NULL DEFAULT false
    - sellers.trust_score INTEGER NOT NULL DEFAULT 0  (CHECK >= 0)
    - new table housing_complexes
    - listings.jk_id UUID FK → housing_complexes.id (optional, coexists
      with free-text listings.jk_name from S3)

T-035 (notification_type enum extension: urgent_match, mortgage_match)
is enforced at the Pydantic / Notification model layer; no DB DDL needed
because that column is already VARCHAR.

Indexes per §4.1 Sprint 7.

Revision ID: s7_roles_media
Revises: s6_property_polish
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa

revision = "s7_roles_media"
down_revision = "s6_property_polish"
branch_labels = None
depends_on = None


def _add_col(table: str, column: str, ddl: str) -> None:
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = '{table}' AND column_name = '{column}'
            ) THEN
                ALTER TABLE {table} ADD COLUMN {column} {ddl};
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    # T-027 / T-028 — sellers extensions
    _add_col(
        "sellers",
        "is_developer_verified",
        "BOOLEAN NOT NULL DEFAULT false",
    )
    _add_col("sellers", "trust_score", "INTEGER NOT NULL DEFAULT 0")
    op.create_check_constraint(
        "ck_sellers_trust_score_nonneg",
        "sellers",
        "trust_score >= 0",
    )

    # T-027 — housing_complexes table
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS housing_complexes (
            id UUID PRIMARY KEY,
            name VARCHAR(200) NOT NULL,
            developer_id UUID NULL REFERENCES sellers(id) ON DELETE SET NULL,
            region VARCHAR(100) NULL,
            district VARCHAR(100) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_housing_complexes_developer_id "
        "ON housing_complexes(developer_id);"
    )

    # T-027 — listings.jk_id (optional FK)
    _add_col(
        "listings",
        "jk_id",
        "UUID NULL REFERENCES housing_complexes(id) ON DELETE SET NULL",
    )

    # Sprint 7 indexes (§4.1)
    op.create_index(
        "idx_listings_jk_id",
        "listings",
        ["jk_id"],
        postgresql_where=sa.text("jk_id IS NOT NULL"),
    )
    op.create_index(
        "idx_sellers_trust_score",
        "sellers",
        ["trust_score"],
        postgresql_where=sa.text("trust_score > 0"),
    )


def downgrade() -> None:
    op.drop_index("idx_sellers_trust_score", table_name="sellers")
    op.drop_index("idx_listings_jk_id", table_name="listings")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS jk_id;")
    op.execute("DROP TABLE IF EXISTS housing_complexes;")
    op.execute(
        "ALTER TABLE sellers DROP CONSTRAINT IF EXISTS ck_sellers_trust_score_nonneg;"
    )
    op.execute("ALTER TABLE sellers DROP COLUMN IF EXISTS trust_score;")
    op.execute("ALTER TABLE sellers DROP COLUMN IF EXISTS is_developer_verified;")
