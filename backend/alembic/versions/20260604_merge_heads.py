"""merge phase2_block_merge and prp_listing_prompt_v2 heads

Revision ID: merge_phase2_and_prp_v2
Revises: 11640c79759c, prp_listing_prompt_v2
Create Date: 2026-06-04

Two migration branches diverged from pro_block_f_ai_foundation:
  A: pro_block_f_ai_foundation → prp_block_f_synonyms → prq_block_f_exports
     → (prr/prs/prt/pru parallel) → 11640c79759c (phase2_block_merge)
  B: pro_block_f_ai_foundation → prp_listing_prompt_v2

This migration merges both heads into a single linear chain.
"""
from alembic import op

revision = "merge_phase2_and_prp_v2"
down_revision = ("11640c79759c", "prp_listing_prompt_v2")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
