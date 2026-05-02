"""Add region column to telegram_listings and olx_listings, backfill from district.

Revision ID: add_region_to_crawler_tables
Revises: normalize_listing_type_enums
"""

import sqlalchemy as sa
from alembic import op

revision = "add_region_to_crawler_tables"
down_revision = "normalize_listing_type_enums"
branch_labels = None
depends_on = None

# District alias → canonical district key (same as regions.py _DISTRICT_ALIASES)
_DISTRICT_ALIASES = {
    "bektemir": "bektemir",
    "chilonzor": "chilonzor", "chilanzar": "chilonzor",
    "mirzo ulug'bek": "mirzo_ulugbek", "mirzo ulugbek": "mirzo_ulugbek",
    "mirzo-ulugbekskiy rayon": "mirzo_ulugbek",
    "mirobod": "mirobod", "mirabad": "mirobod",
    "olmazor": "olmazor",
    "sergeli": "sergeli", "sergili": "sergeli",
    "shayxontohur": "shayxontohur", "shaykhontohur": "shayxontohur",
    "uchtepa": "uchtepa",
    "yakkasaroy": "yakkasaroy", "yakkasaray": "yakkasaroy",
    "yashnobod": "yashnobod",
    "yunusobod": "yunusobod", "yunusabad": "yunusobod",
    "chirchiq": "chirchiq", "olmaliq": "olmaliq", "angren": "angren",
    "nurafshon": "nurafshon",
    "andijon": "andijon_sh", "andijan": "andijon_sh",
    "asaka": "asaka",
    "buloqboshi": "buloqboshi", "bulokboshi": "buloqboshi",
    "samarqand": "samarqand_sh", "samarkand": "samarqand_sh",
    "namangan": "namangan_sh",
    "fargona": "fargona_sh", "fergana": "fargona_sh",
    "buxoro": "buxoro_sh", "bukhara": "buxoro_sh",
    "nukus": "nukus_sh",
    "qarshi": "qarshi_sh",
    "termiz": "termiz_sh", "termez": "termiz_sh",
    "urganch": "urganch_sh",
    "jizzax": "jizzax_sh", "jizzakh": "jizzax_sh",
    "navoiy": "navoiy_sh", "navoi": "navoiy_sh",
    "guliston": "guliston_sh",
    # Cyrillic
    "мирзо-улугбекский район": "mirzo_ulugbek",
    "5-микрорайон": "mirzo_ulugbek",
}

# Canonical district key → region key
_DISTRICT_TO_REGION = {
    "bektemir": "toshkent_shahri", "chilonzor": "toshkent_shahri",
    "mirzo_ulugbek": "toshkent_shahri", "mirobod": "toshkent_shahri",
    "olmazor": "toshkent_shahri", "sergeli": "toshkent_shahri",
    "shayxontohur": "toshkent_shahri", "uchtepa": "toshkent_shahri",
    "yakkasaroy": "toshkent_shahri", "yashnobod": "toshkent_shahri",
    "yunusobod": "toshkent_shahri",
    "chirchiq": "toshkent_viloyati", "olmaliq": "toshkent_viloyati",
    "angren": "toshkent_viloyati", "nurafshon": "toshkent_viloyati",
    "andijon_sh": "andijon", "asaka": "andijon",
    "buloqboshi": "andijon", "xo_jaobod": "andijon",
    "samarqand_sh": "samarqand",
    "namangan_sh": "namangan",
    "fargona_sh": "fargona",
    "buxoro_sh": "buxoro",
    "nukus_sh": "qoraqalpogiston",
    "qarshi_sh": "qashqadaryo",
    "termiz_sh": "surxondaryo",
    "urganch_sh": "xorazm",
    "jizzax_sh": "jizzax",
    "navoiy_sh": "navoiy",
    "guliston_sh": "sirdaryo",
}


def _resolve_region(district: str) -> str | None:
    """Resolve a district string to a region key."""
    if not district:
        return None
    norm = district.lower().strip()
    alias_key = _DISTRICT_ALIASES.get(norm)
    if alias_key:
        return _DISTRICT_TO_REGION.get(alias_key)
    slug = norm.replace(" ", "_").replace("'", "_").replace("\u2018", "_").replace("-", "_")
    return _DISTRICT_TO_REGION.get(slug)


def upgrade() -> None:
    # Add region column to both tables
    op.add_column("telegram_listings", sa.Column("region", sa.String(100), nullable=True))
    op.create_index("ix_telegram_listings_region", "telegram_listings", ["region"])

    op.add_column("olx_listings", sa.Column("region", sa.String(100), nullable=True))
    op.create_index("ix_olx_listings_region", "olx_listings", ["region"])

    # Backfill: read all rows with non-null district, compute region, update
    conn = op.get_bind()

    for table in ("telegram_listings", "olx_listings"):
        rows = conn.execute(
            sa.text(f"SELECT id, district FROM {table} WHERE district IS NOT NULL AND region IS NULL")
        ).fetchall()

        for row_id, district in rows:
            region = _resolve_region(district)
            if region:
                conn.execute(
                    sa.text(f"UPDATE {table} SET region = :region WHERE id = :id"),
                    {"region": region, "id": row_id},
                )


def downgrade() -> None:
    op.drop_index("ix_olx_listings_region", table_name="olx_listings")
    op.drop_column("olx_listings", "region")
    op.drop_index("ix_telegram_listings_region", table_name="telegram_listings")
    op.drop_column("telegram_listings", "region")
