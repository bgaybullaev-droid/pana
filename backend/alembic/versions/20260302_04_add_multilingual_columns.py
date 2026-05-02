"""Add multilingual columns for listing content translation.

Adds original_language, description_ru/uz, address_ru/uz, title_ru/uz (listings only),
translation_status, translated_at to all three listing tables.
Backfills original_language from character-set heuristic and copies existing content.

Revision ID: add_multilingual_columns
Revises: backfill_district_from_addr
"""

import re

import sqlalchemy as sa
from alembic import op

revision = "add_multilingual_columns"
down_revision = "backfill_district_from_addr"
branch_labels = None
depends_on = None

# Uzbek-specific Cyrillic characters (not present in Russian)
_UZ_CYRILLIC = set("ҳғқўҲҒҚЎ")


def _detect_language(text: str) -> str:
    """Detect language from text using character-set heuristic."""
    if not text:
        return "ru"
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    total = cyrillic + latin
    if total == 0:
        return "ru"
    # Check for Uzbek-specific Cyrillic chars
    if cyrillic > 0 and any(ch in _UZ_CYRILLIC for ch in text):
        return "uz"
    if cyrillic / total > 0.5:
        return "ru"
    return "uz"


def upgrade() -> None:
    # ── Add columns to listings ──
    op.add_column("listings", sa.Column("original_language", sa.String(5), nullable=True))
    op.add_column("listings", sa.Column("title_ru", sa.String(200), nullable=True))
    op.add_column("listings", sa.Column("title_uz", sa.String(200), nullable=True))
    op.add_column("listings", sa.Column("description_ru", sa.Text, nullable=True))
    op.add_column("listings", sa.Column("description_uz", sa.Text, nullable=True))
    op.add_column("listings", sa.Column("address_ru", sa.String(500), nullable=True))
    op.add_column("listings", sa.Column("address_uz", sa.String(500), nullable=True))
    op.add_column("listings", sa.Column("translation_status", sa.String(20), server_default="pending", nullable=True))
    op.add_column("listings", sa.Column("translated_at", sa.DateTime, nullable=True))

    # ── Add columns to telegram_listings ──
    op.add_column("telegram_listings", sa.Column("original_language", sa.String(5), nullable=True))
    op.add_column("telegram_listings", sa.Column("description_ru", sa.Text, nullable=True))
    op.add_column("telegram_listings", sa.Column("description_uz", sa.Text, nullable=True))
    op.add_column("telegram_listings", sa.Column("address_ru", sa.String(500), nullable=True))
    op.add_column("telegram_listings", sa.Column("address_uz", sa.String(500), nullable=True))
    op.add_column("telegram_listings", sa.Column("translation_status", sa.String(20), server_default="pending", nullable=True))
    op.add_column("telegram_listings", sa.Column("translated_at", sa.DateTime, nullable=True))

    # ── Add columns to olx_listings ──
    op.add_column("olx_listings", sa.Column("original_language", sa.String(5), nullable=True))
    op.add_column("olx_listings", sa.Column("description_ru", sa.Text, nullable=True))
    op.add_column("olx_listings", sa.Column("description_uz", sa.Text, nullable=True))
    op.add_column("olx_listings", sa.Column("address_ru", sa.String(500), nullable=True))
    op.add_column("olx_listings", sa.Column("address_uz", sa.String(500), nullable=True))
    op.add_column("olx_listings", sa.Column("translation_status", sa.String(20), server_default="pending", nullable=True))
    op.add_column("olx_listings", sa.Column("translated_at", sa.DateTime, nullable=True))

    # ── Backfill existing data ──
    conn = op.get_bind()

    for table, has_title in [("listings", True), ("telegram_listings", False), ("olx_listings", False)]:
        text_col = "description" if not has_title else "COALESCE(description, title, '')"
        rows = conn.execute(
            sa.text(f"SELECT id, {text_col} AS detect_text, description, address"
                    + (", title" if has_title else "")
                    + f" FROM {table}")
        ).fetchall()

        for row in rows:
            lang = _detect_language(row.detect_text or "")
            updates = {"lang": lang, "id": row.id}

            if lang == "ru":
                set_parts = ["original_language = :lang"]
                if row.description:
                    set_parts.append("description_ru = :desc")
                    updates["desc"] = row.description
                if row.address:
                    set_parts.append("address_ru = :addr")
                    updates["addr"] = row.address
                if has_title and getattr(row, "title", None):
                    set_parts.append("title_ru = :title")
                    updates["title"] = row.title
            elif lang == "uz":
                set_parts = ["original_language = :lang"]
                if row.description:
                    set_parts.append("description_uz = :desc")
                    updates["desc"] = row.description
                if row.address:
                    set_parts.append("address_uz = :addr")
                    updates["addr"] = row.address
                if has_title and getattr(row, "title", None):
                    set_parts.append("title_uz = :title")
                    updates["title"] = row.title
            else:
                set_parts = ["original_language = :lang", "translation_status = 'skipped'"]

            conn.execute(
                sa.text(f"UPDATE {table} SET {', '.join(set_parts)} WHERE id = :id"),
                updates,
            )

        print(f"  {table}: backfilled original_language for {len(rows)} rows")

    # Set default for non-null after backfill
    op.alter_column("listings", "original_language", server_default="ru", nullable=False)
    op.alter_column("telegram_listings", "original_language", server_default="ru", nullable=False)
    op.alter_column("olx_listings", "original_language", server_default="ru", nullable=False)


def downgrade() -> None:
    for table in ("listings", "telegram_listings", "olx_listings"):
        op.drop_column(table, "translated_at")
        op.drop_column(table, "translation_status")
        op.drop_column(table, "address_uz")
        op.drop_column(table, "address_ru")
        op.drop_column(table, "description_uz")
        op.drop_column(table, "description_ru")
        op.drop_column(table, "original_language")

    op.drop_column("listings", "title_uz")
    op.drop_column("listings", "title_ru")
