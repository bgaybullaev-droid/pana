"""prp_block_f_synonyms — Block F V2.0 (F2) synonym dictionary.

One table: ``synonym_entries``. Drives the rule-based synonym matcher
behind ``POST /listings/{id}/analyse-text`` and the admin
``/admin/synonyms`` console.

Revision ID: prp_block_f_synonyms
Revises: pro_block_f_ai_foundation
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "prp_block_f_synonyms"
down_revision: str | None = "pro_block_f_ai_foundation"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "synonym_entries",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("parameter_key", sa.String(64), nullable=False),
        sa.Column("parameter_value", sa.String(64), nullable=True),
        sa.Column("surface_form", sa.String(128), nullable=False),
        sa.Column("language", sa.String(8), nullable=False),
        sa.Column(
            "polarity",
            sa.String(8),
            nullable=False,
            server_default=sa.text("'positive'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_synonym_param_lang",
        "synonym_entries",
        ["parameter_key", "language"],
    )
    op.create_index(
        "idx_synonym_surface_lang",
        "synonym_entries",
        ["surface_form", "language"],
    )
    # Uniqueness includes parameter_value via COALESCE so two rows with
    # NULL parameter_value but otherwise identical aren't both allowed.
    op.execute(
        """
        CREATE UNIQUE INDEX uq_synonym_uniq ON synonym_entries (
            parameter_key,
            COALESCE(parameter_value, ''),
            surface_form,
            language
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_synonym_uniq;")
    op.drop_index("idx_synonym_surface_lang", table_name="synonym_entries")
    op.drop_index("idx_synonym_param_lang", table_name="synonym_entries")
    op.drop_table("synonym_entries")
