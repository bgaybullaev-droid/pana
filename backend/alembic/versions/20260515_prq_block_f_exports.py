"""prq_block_f_exports — Block F V2.0 (F4a) cabinet exports.

Adds ``export_templates`` table and three nullable columns on
``sellers`` for the per-seller export signature / CTA / extra hashtags.

Revision ID: prq_block_f_exports
Revises: prp_block_f_synonyms
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "prq_block_f_exports"
down_revision: str | None = "prp_block_f_synonyms"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "export_templates",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column("template_body", sa.Text, nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_export_template_active
            ON export_templates (platform, language)
            WHERE is_active;
        """
    )

    op.add_column(
        "sellers",
        sa.Column("export_signature", sa.Text, nullable=True),
    )
    op.add_column(
        "sellers",
        sa.Column("export_cta", sa.Text, nullable=True),
    )
    op.add_column(
        "sellers",
        sa.Column("export_extra_hashtags", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sellers", "export_extra_hashtags")
    op.drop_column("sellers", "export_cta")
    op.drop_column("sellers", "export_signature")
    op.execute("DROP INDEX IF EXISTS uq_export_template_active;")
    op.drop_table("export_templates")
