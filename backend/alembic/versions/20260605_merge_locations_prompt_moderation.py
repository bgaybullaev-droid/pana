"""Merge three diverged heads into a single chain.

``rename_city_district_keys`` has three descendants that were added
independently:

  1. ``prp_listing_prompt_v3``     — AI prompt v3 data
  2. ``seed_locations``            — landmarks + housing-complex seed
     (itself a child of ``landmarks_and_hc_geo``)
  3. ``backfill_draft_moderation`` — approve ACTIVE+PENDING manual listings

Each was authored in isolation, producing multiple heads and causing
``alembic upgrade head`` to fail on the VPS.  This merge revision creates
a single head so deployments proceed normally again.

Revision ID: merge_loc_prompt_moderation
Revises: prp_listing_prompt_v3, seed_locations, backfill_draft_moderation
Create Date: 2026-06-05
"""
from alembic import op  # noqa: F401  (required by Alembic discovery)

# NB: keep this id <= 32 chars — alembic stores it in
# alembic_version.version_num which is VARCHAR(32). The original
# "merge_locations_prompt_moderation" (33 chars) overflowed and aborted the
# version-bookkeeping UPDATE at the end of `alembic upgrade head` on deploy
# (psycopg2 StringDataRightTruncation), rolling back the whole upgrade.
revision = "merge_loc_prompt_moderation"
down_revision = (
    "prp_listing_prompt_v3",
    "seed_locations",
    "backfill_draft_moderation",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass  # merge-only; DDL is in the constituent migrations


def downgrade() -> None:
    pass
