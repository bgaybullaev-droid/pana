#!/usr/bin/env python3
"""
Idempotent backfill script for region/district data.

Fills NULL region/district fields across listings, telegram_listings,
and olx_listings using existing inference logic from app.core.regions.

Safe to run multiple times — only fills NULL fields, never overwrites
existing data.

Usage:
    python backend/scripts/backfill_location.py [--dry-run]

    --dry-run   Show what would change without modifying the database.

Requires: psycopg2-binary
"""

import argparse
import sys
from typing import Optional

import psycopg2

# ── Connection config ────────────────────────────────────────────────
DB_HOST = "192.168.0.189"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASS = "web@1234"
DB_NAME = "real_estate"

TABLES = ["listings", "telegram_listings", "olx_listings"]

# ── Inline region inference logic (mirrors backend/app/core/regions.py) ──
# We inline it to avoid importing the full app (which requires env vars).

REGIONS: dict[str, list[str]] = {
    "qoraqalpogiston": [
        "nukus_sh", "nukus_t", "amudaryo", "beruniy", "chimboy",
        "ellikqala", "kegeyli", "moynaq", "qanliko_l", "qo_ng_irot",
        "qorao_zak", "shumanay", "taxiatosh", "taxtako_pir", "to_rtko_l",
        "xo_jayli", "bo_zatov",
    ],
    "andijon": [
        "andijon_sh", "xonobod_sh", "andijon_t", "asaka", "baliqchi",
        "bo_ston", "buloqboshi", "izboskan", "jalaquduq", "xo_jaobod",
        "qo_rg_ontepa", "marhamat", "oltinko_l", "paxtaobod", "shahrixon",
        "ulug_nor",
    ],
    "buxoro": [
        "buxoro_sh", "kogon_sh", "buxoro_t", "g_ijduvon", "jondor",
        "kogon_t", "olot", "peshku", "qorako_l", "qorovulbozor",
        "romitan", "shofirkon", "vobkent",
    ],
    "fargona": [
        "fargona_sh", "qo_qon_sh", "marg_ilon_sh", "quvasoy_sh", "fargona_t",
        "beshariq", "bog_dod", "buvayda", "dang_ara", "furqat",
        "yozyovon", "quva", "oltiariq", "o_zbekiston", "qo_shtepa",
        "rishton", "so_x", "toshloq", "uchko_prik",
    ],
    "jizzax": [
        "jizzax_sh", "arnasoy", "baxmal", "do_stlik",
        "forish", "g_allaorol", "sharof_rashidov",
        "mirzacho_l", "paxtakor", "yangiobod", "zafarobod",
        "zarbdor", "zomin",
    ],
    "xorazm": [
        "urganch_sh", "xiva_sh", "urganch_t", "bog_ot", "gurlan",
        "xazorasp", "xiva_t", "xonqa", "qo_shko_pir", "shovot",
        "yangiariq", "yangibozor", "tuproqqala",
    ],
    "namangan": [
        "namangan_sh", "namangan_t", "chortoq", "chust",
        "kosonsoy", "mingbuloq", "norin", "pop",
        "to_raqo_rg_on", "uchqo_rg_on", "uychi", "yangiqo_rg_on",
    ],
    "navoiy": [
        "navoiy_sh", "zarafshon_sh", "g_ozg_on_sh", "karmana", "konimex",
        "navbahor", "nurota", "qiziltepa", "tomdi", "uchquduq",
        "xatirchi",
    ],
    "qashqadaryo": [
        "qarshi_sh", "shahrisabz_sh", "qarshi_t", "chiroqchi", "dehqonobod",
        "g_uzor", "kasbi", "kitob", "ko_kdala", "koson",
        "mirishkor", "muborak", "nishon", "shahrisabz_t", "yakkabog_",
        "qamashi",
    ],
    "samarqand": [
        "samarqand_sh", "kattaqo_rg_on_sh", "samarqand_t", "kattaqo_rg_on_t", "bulung_ur",
        "ishtixon", "jomboy", "narpay", "nurobod", "oqdaryo",
        "pastdarg_om", "payariq", "paxtachi", "qo_shrabot", "toyloq",
        "urgut",
    ],
    "sirdaryo": [
        "guliston_sh", "shirin_sh", "yangiyer_sh", "guliston_t", "boyovut",
        "hovos", "mirzaobod", "oqoltin", "sardoba", "sayxunobod",
        "sirdaryo_t",
    ],
    "surxondaryo": [
        "termiz_sh", "termiz_t", "angor", "bandixon",
        "boysun", "denov", "jarqo_rg_on", "muzrabod",
        "oltinsoy", "qiziriq", "qumqo_rg_on", "sariosiyo",
        "sherobod", "sho_rchi", "uzun",
    ],
    "toshkent_viloyati": [
        "nurafshon_sh", "olmaliq_sh", "angren_sh", "bekobod_sh", "chirchiq_sh",
        "ohangaron_sh", "yangiyo_l_sh", "bekobod_t", "ohangaron_t", "yangiyo_l_t",
        "bo_ka", "bo_stonliq", "chinoz", "qibray", "oqqo_rg_on",
        "parkent", "piskent", "toshkent_t", "zangiota", "yuqorichirchiq",
        "o_rtachirchiq", "quyi_chirchiq",
    ],
    "toshkent_shahri": [
        "bektemir", "chilonzor", "mirzo_ulugbek", "mirobod",
        "olmazor", "sergeli", "shayxontohur", "uchtepa",
        "yakkasaroy", "yashnobod", "yunusobod",
    ],
}

DISTRICT_TO_REGION: dict[str, str] = {}
for _region, _districts in REGIONS.items():
    for _district in _districts:
        DISTRICT_TO_REGION[_district] = _region

ALL_DISTRICTS = set(DISTRICT_TO_REGION.keys())
VALID_REGIONS = set(REGIONS.keys())

_DISTRICT_ALIASES: dict[str, str] = {
    "bektemir": "bektemir",
    "chilonzor": "chilonzor", "chilanзar": "chilonzor", "chilanzar": "chilonzor",
    "mirzo_ulugbek": "mirzo_ulugbek", "mirzo ulug'bek": "mirzo_ulugbek",
    "mirzo ulugbek": "mirzo_ulugbek", "mirzo-ulugbekskiy rayon": "mirzo_ulugbek",
    "мирзо-улугбекский район": "mirzo_ulugbek", "мирзо-улугбекский": "mirzo_ulugbek",
    "mirobod": "mirobod", "mirabad": "mirobod", "мирабадский": "mirobod",
    "olmazor": "olmazor", "алмазарский": "olmazor",
    "sergeli": "sergeli", "sergili": "sergeli", "сергелийский": "sergeli",
    "shayxontohur": "shayxontohur", "shaykhontohur": "shayxontohur",
    "шайхантаурский": "shayxontohur",
    "uchtepa": "uchtepa", "учтепинский": "uchtepa",
    "yakkasaroy": "yakkasaroy", "yakkasaray": "yakkasaroy",
    "яккасарайский": "yakkasaroy",
    "yashnobod": "yashnobod", "яшнабадский": "yashnobod",
    "yunusobod": "yunusobod", "yunusabad": "yunusobod", "юнусабадский": "yunusobod",
    "chirchiq": "chirchiq_sh", "olmaliq": "olmaliq_sh", "angren": "angren_sh",
    "nurafshon": "nurafshon_sh",
    "andijon": "andijon_sh", "andijan": "andijon_sh",
    "asaka": "asaka",
    "buloqboshi": "buloqboshi", "bulokboshi": "buloqboshi",
    "xo'jaobod": "xo_jaobod", "xojaobod": "xo_jaobod",
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
    "darhan": "zangiota",
    "g'ormiron": "kosonsoy",
    "qamashi": "qamashi",
}

_REGION_NAME_ALIASES: dict[str, str] = {
    "tashkent": "toshkent_shahri",
    "toshkent": "toshkent_shahri",
    "ташкент": "toshkent_shahri",
}

_ADDRESS_LANDMARKS: dict[str, tuple[str, str]] = {
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
    "darxan": ("zangiota", "toshkent_viloyati"),
    "дархан": ("zangiota", "toshkent_viloyati"),
    "клара цеткин": ("andijon_sh", "andijon"),
    "klara tsetkin": ("andijon_sh", "andijon"),
    "koson": ("qamashi", "qashqadaryo"),
    "косон": ("qamashi", "qashqadaryo"),
}


def resolve_district_alias(district: str) -> Optional[str]:
    """Resolve a display-name district to its canonical key."""
    if district in ALL_DISTRICTS:
        return district
    normalized = district.lower().strip()
    alias = _DISTRICT_ALIASES.get(normalized)
    if alias and alias in ALL_DISTRICTS:
        return alias
    slug = normalized.replace(" ", "_").replace("'", "_").replace("\u2019", "_").replace("-", "_")
    if slug in ALL_DISTRICTS:
        return slug
    return None


def infer_region(district: str) -> Optional[str]:
    """Infer region key from a district string."""
    if not district:
        return None
    # 1. Canonical key
    if district in DISTRICT_TO_REGION:
        return DISTRICT_TO_REGION[district]
    # 2. Alias lookup
    canonical = resolve_district_alias(district)
    if canonical:
        return DISTRICT_TO_REGION.get(canonical)
    # 3. Region-name fallback (e.g. "Tashkent" used as district)
    normalized = district.lower().strip()
    slug = normalized.replace(" ", "_").replace("'", "_").replace("\u2019", "_").replace("-", "_")
    region = _REGION_NAME_ALIASES.get(normalized) or _REGION_NAME_ALIASES.get(slug)
    if region and region in VALID_REGIONS:
        return region
    return None


def infer_district_from_address(address: str) -> Optional[tuple[str, str]]:
    """Infer (district_key, region_key) from address landmarks."""
    if not address:
        return None
    normalized = address.lower().strip()
    for keyword, district_region in _ADDRESS_LANDMARKS.items():
        if keyword in normalized:
            return district_region
    return None


# ── Main backfill logic ──────────────────────────────────────────────

def run_audit(cur) -> dict:
    """Run pre/post audit and return stats."""
    stats = {}
    for table in TABLES:
        cur.execute(f"""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN region IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN district IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN region IS NULL AND district IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN district IS NOT NULL AND region IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN region IS NOT NULL AND district IS NULL THEN 1 ELSE 0 END)
            FROM {table}
        """)
        row = cur.fetchone()
        stats[table] = {
            "total": row[0],
            "null_region": row[1],
            "null_district": row[2],
            "both_null": row[3],
            "district_no_region": row[4],
            "region_no_district": row[5],
        }
    return stats


def print_stats(stats: dict, label: str):
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    print(f"  {'Table':<22} {'Total':>6} {'NullReg':>8} {'NullDist':>9} {'BothNull':>9} {'D!R':>5} {'R!D':>5}")
    print(f"  {'-'*22} {'-'*6} {'-'*8} {'-'*9} {'-'*9} {'-'*5} {'-'*5}")
    for table, s in stats.items():
        print(f"  {table:<22} {s['total']:>6} {s['null_region']:>8} {s['null_district']:>9} "
              f"{s['both_null']:>9} {s['district_no_region']:>5} {s['region_no_district']:>5}")


def backfill(dry_run: bool = False):
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )
    cur = conn.cursor()

    # ── Pre-audit ──
    pre_stats = run_audit(cur)
    print_stats(pre_stats, "BEFORE BACKFILL")

    regions_filled = 0
    districts_filled = 0
    districts_normalized = 0
    total_processed = 0

    for table in TABLES:
        print(f"\n--- Processing {table} ---")

        # ── Pass 1: Fill NULL region from existing district ──
        cur.execute(f"""
            SELECT id, district, address
            FROM {table}
            WHERE region IS NULL AND district IS NOT NULL
        """)
        rows = cur.fetchall()
        for row_id, district, address in rows:
            region = infer_region(district)
            if region:
                if not dry_run:
                    cur.execute(
                        f"UPDATE {table} SET region = %s WHERE id = %s AND region IS NULL",
                        (region, row_id),
                    )
                print(f"  [FILL REGION] id={row_id}, district=\"{district}\" -> region=\"{region}\"")
                regions_filled += 1
            else:
                print(f"  [SKIP] id={row_id}, district=\"{district}\" — cannot resolve region")
            total_processed += 1

        # ── Pass 2: Fill NULL district (and region) from address ──
        cur.execute(f"""
            SELECT id, address
            FROM {table}
            WHERE district IS NULL AND address IS NOT NULL AND address != 'None'
        """)
        rows = cur.fetchall()
        for row_id, address in rows:
            result = infer_district_from_address(address)
            if result:
                district_key, region_key = result
                if not dry_run:
                    cur.execute(
                        f"UPDATE {table} SET district = %s, region = COALESCE(region, %s) "
                        f"WHERE id = %s AND district IS NULL",
                        (district_key, region_key, row_id),
                    )
                print(f"  [FILL DISTRICT] id={row_id}, address=\"{address}\" -> "
                      f"district=\"{district_key}\", region=\"{region_key}\"")
                districts_filled += 1
                regions_filled += 1
            else:
                print(f"  [SKIP] id={row_id}, address=\"{address}\" — cannot infer district")
            total_processed += 1

        # ── Pass 3: Normalize non-canonical district names ──
        cur.execute(f"""
            SELECT id, district
            FROM {table}
            WHERE district IS NOT NULL
        """)
        rows = cur.fetchall()
        for row_id, district in rows:
            if district in ALL_DISTRICTS:
                continue  # Already canonical
            canonical = resolve_district_alias(district)
            if canonical and canonical != district:
                if not dry_run:
                    cur.execute(
                        f"UPDATE {table} SET district = %s WHERE id = %s",
                        (canonical, row_id),
                    )
                print(f"  [NORMALIZE] id={row_id}, \"{district}\" -> \"{canonical}\"")
                districts_normalized += 1
            total_processed += 1

    if not dry_run:
        conn.commit()
        print("\n  ** Changes committed **")
    else:
        conn.rollback()
        print("\n  ** DRY RUN — no changes made **")

    # ── Post-audit ──
    if not dry_run:
        post_stats = run_audit(cur)
        print_stats(post_stats, "AFTER BACKFILL")

    print(f"\n{'=' * 60}")
    print(f"  SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total records inspected:     {total_processed}")
    print(f"  Regions filled:              {regions_filled}")
    print(f"  Districts filled:            {districts_filled}")
    print(f"  Districts normalized:        {districts_normalized}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill NULL region/district data")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying DB")
    args = parser.parse_args()

    backfill(dry_run=args.dry_run)
