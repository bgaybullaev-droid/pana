"""phase2_block_merge

Revision ID: 11640c79759c
Revises: prr_listing_sale, prs_promotions_banners, prt_referral_program, pru_crm_suspicions
Create Date: 2026-05-14 11:07:20.638143

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '11640c79759c'
down_revision: Union[str, None] = ('prr_listing_sale', 'prs_promotions_banners', 'prt_referral_program', 'pru_crm_suspicions')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
