"""Add region column to listings and convert district names to keys.

Revision ID: add_region_to_listings
Revises: add_seller_source_channel
Create Date: 2026-02-26
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "add_region_to_listings"
down_revision = "add_seller_source_channel"
branch_labels = None
depends_on = None

# Existing Russian district names → new key
DISTRICT_MAP = {
    "Мирзо-Улугбекский": "mirzo_ulugbek",
    "Яккасарайский": "yakkasaroy",
    "Чиланзарский": "chilonzor",
    "Сергелийский": "sergeli",
    "Юнусабадский": "yunusobod",
    "Шайхантаурский": "shayxontohur",
    "Учтепинский": "uchtepa",
    "Алмазарский": "olmazor",
    "Бектемирский": "bektemir",
    "Мирабадский": "mirobod",
    "Яшнабадский": "yashnobod",
}

REVERSE_MAP = {v: k for k, v in DISTRICT_MAP.items()}


def upgrade() -> None:
    # 1. Add region column
    op.add_column("listings", sa.Column("region", sa.String(100), nullable=True))
    op.create_index("ix_listings_region", "listings", ["region"])

    # 2. Convert existing Russian district names to keys + set region
    case_parts = " ".join(
        f"WHEN district = '{russian}' THEN '{key}'"
        for russian, key in DISTRICT_MAP.items()
    )
    in_values = ", ".join(f"'{r}'" for r in DISTRICT_MAP.keys())

    op.execute(
        f"UPDATE listings "
        f"SET district = CASE {case_parts} ELSE district END, "
        f"    region = CASE WHEN district IN ({in_values}) THEN 'toshkent_shahri' ELSE region END "
        f"WHERE district IS NOT NULL"
    )

    # 3. Composite index for region+district filtering
    op.create_index("ix_listings_region_district", "listings", ["region", "district"])


def downgrade() -> None:
    # Reverse district keys back to Russian names
    case_parts = " ".join(
        f"WHEN district = '{key}' THEN '{russian}'"
        for key, russian in REVERSE_MAP.items()
    )
    in_values = ", ".join(f"'{k}'" for k in REVERSE_MAP.keys())

    op.execute(
        f"UPDATE listings "
        f"SET district = CASE {case_parts} ELSE district END "
        f"WHERE district IN ({in_values})"
    )

    op.drop_index("ix_listings_region_district")
    op.drop_index("ix_listings_region")
    op.drop_column("listings", "region")
