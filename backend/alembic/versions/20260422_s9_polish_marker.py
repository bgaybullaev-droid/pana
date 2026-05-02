"""Sprint 9 — Polish (T-017, T-038, T-039). No schema change.

Blueprint §1.2 Sprint 9 explicitly carries 0 new columns. T-017 is a
code-only validator pass; T-038 is a frontend currency-display feature
(uses cached USD/UZS rate; no DB); T-039 is i18n only; T-012 stays
deferred per blueprint open decisions.

This migration is a no-op marker so the alembic head clearly lands on
Sprint 9. Useful for tooling that asks "what's the current sprint?".

Revision ID: s9_polish_marker
Revises: s8_discoverability
Create Date: 2026-04-22
"""

revision = "s9_polish_marker"
down_revision = "s8_discoverability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
