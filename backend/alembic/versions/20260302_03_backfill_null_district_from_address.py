"""Backfill NULL district records using address landmark matching.

Revision ID: backfill_null_district_from_address
Revises: add_region_to_crawler_tables
"""

import sqlalchemy as sa
from alembic import op

revision = "backfill_district_from_addr"
down_revision = "add_region_to_crawler_tables"
branch_labels = None
depends_on = None

# Inline copy of landmark mapping (migrations must be self-contained)
_ADDRESS_LANDMARKS = {
    # toshkent_shahri
    "akay city": ("sergeli", "toshkent_shahri"),
    "basri baba": ("sergeli", "toshkent_shahri"),
    "basribaba": ("sergeli", "toshkent_shahri"),
    "poytaxt gavhari": ("sergeli", "toshkent_shahri"),
    "mahtumkuli": ("yakkasaroy", "toshkent_shahri"),
    "махтумкули": ("yakkasaroy", "toshkent_shahri"),
    "mahtu": ("yakkasaroy", "toshkent_shahri"),
    "ipak yuli": ("mirzo_ulugbek", "toshkent_shahri"),
    "ipak yo'li": ("mirzo_ulugbek", "toshkent_shahri"),
    "ипак йули": ("mirzo_ulugbek", "toshkent_shahri"),
    "parkentsk": ("mirzo_ulugbek", "toshkent_shahri"),
    "alaisky": ("yakkasaroy", "toshkent_shahri"),
    "alaysk": ("yakkasaroy", "toshkent_shahri"),
    "алайский": ("yakkasaroy", "toshkent_shahri"),
    "financial institute": ("yakkasaroy", "toshkent_shahri"),
    "sayahat": ("chilonzor", "toshkent_shahri"),
    "sayohat": ("chilonzor", "toshkent_shahri"),
    "anhor": ("mirobod", "toshkent_shahri"),
    "анхор": ("mirobod", "toshkent_shahri"),
    "german embassy": ("mirobod", "toshkent_shahri"),
    "orikzor": ("uchtepa", "toshkent_shahri"),
    "урикзор": ("uchtepa", "toshkent_shahri"),
    # toshkent_viloyati
    "darxan": ("zangiota", "toshkent_viloyati"),
    "дархан": ("zangiota", "toshkent_viloyati"),
    # andijon
    "клара цеткин": ("andijon_sh", "andijon"),
    "klara tsetkin": ("andijon_sh", "andijon"),
    # qashqadaryo
    "koson": ("qamashi", "qashqadaryo"),
    "косон": ("qamashi", "qashqadaryo"),
}


def _infer_from_address(address):
    if not address:
        return None
    normalized = address.lower().strip()
    for keyword, district_region in _ADDRESS_LANDMARKS.items():
        if keyword in normalized:
            return district_region
    return None


def upgrade() -> None:
    conn = op.get_bind()

    for table in ("telegram_listings", "olx_listings", "listings"):
        rows = conn.execute(
            sa.text(
                f"SELECT id, address FROM {table} "
                f"WHERE district IS NULL AND address IS NOT NULL"
            )
        ).fetchall()

        updated = 0
        for row_id, address in rows:
            result = _infer_from_address(address)
            if result:
                district, region = result
                conn.execute(
                    sa.text(
                        f"UPDATE {table} SET district = :district, region = :region "
                        f"WHERE id = :id"
                    ),
                    {"district": district, "region": region, "id": row_id},
                )
                updated += 1

        print(f"  {table}: backfilled {updated} of {len(rows)} NULL-district records")


def downgrade() -> None:
    # Data-only migration; downgrade is a no-op.
    pass
