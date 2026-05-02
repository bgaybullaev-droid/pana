"""Run pending translations for all listing tables.

Usage:
  python3 scripts/run_translations.py                    # uses TRANSLATION_PROVIDER from .env
  python3 scripts/run_translations.py --provider openai  # force OpenAI
  python3 scripts/run_translations.py --provider gemini  # force Gemini
"""
import argparse
import json
import re
import sys
import os
import time

import psycopg2

# Add project root to path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.translation_llm import call_translation_llm

# --- DB Config (reads from same .env as the app) ---
from app.core.config import settings

DB_PARAMS = dict(
    host=settings.postgres_host,
    port=settings.postgres_port,
    user=settings.postgres_user,
    password=settings.postgres_password,
    dbname=settings.postgres_db,
)

LANG_NAMES = {"ru": "Russian", "uz": "Uzbek", "en": "English"}
UZ_CYRILLIC = set("ҳғқўҲҒҚЎ")
UZ_LATIN_MARKERS = {
    "xona", "xonadon", "kvartira", "uy", "sotix", "qavatda", "qavat",
    "mebel", "jihozlar", "hammom", "oshxona", "balkon", "temir",
    "yangi", "qurilish", "ijaraga", "sotiladi", "narx",
    "tuman", "shahar", "viloyat", "mahalla",
    "koladi", "bor", "uchun", "bilan",
}

TRANSLATE_PROMPT = (
    "Translate the following real estate listing fields from {source_lang} to {target_lang}.\n"
    "Preserve proper nouns, landmark names, district names, street names, metro stations, "
    "measurements (m², sotka), and phone numbers exactly as-is.\n"
    'Return ONLY valid JSON with these keys (omit key if input is empty/null):\n'
    '{{"description": "...", "address": "..."}}\n\n'
    "Input:\n"
    "description: {description}\n"
    "address: {address}"
)


def detect_language(text):
    if not text:
        return "ru"
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    total = cyrillic + latin
    if total == 0:
        return "ru"
    if cyrillic > 0 and any(ch in UZ_CYRILLIC for ch in text):
        return "uz"
    if latin > 0:
        words = set(re.findall(r"[a-zA-Z']+", text.lower()))
        uz_hits = words & UZ_LATIN_MARKERS
        if len(uz_hits) >= 2:
            return "uz"
    if total > 0 and cyrillic / total > 0.5:
        return "ru"
    return "en"


def get_targets(lang):
    if lang == "ru":
        return ["uz"]
    elif lang == "uz":
        return ["ru"]
    return ["ru", "uz"]


def process_table(conn, table, provider):
    cur = conn.cursor()
    cur.execute(
        f"SELECT id, description, address, original_language, description_ru, description_uz "
        f"FROM {table} WHERE translation_status = 'pending' ORDER BY created_at"
    )
    rows = cur.fetchall()
    print(f"\n{'='*60}")
    print(f"Processing {table}: {len(rows)} pending (provider: {provider})")
    print(f"{'='*60}")

    success = 0
    failed = 0

    for i, (lid, desc, addr, orig_lang, desc_ru, desc_uz) in enumerate(rows):
        desc = desc or ""
        addr = addr or ""
        if not desc and not addr:
            cur.execute(f"UPDATE {table} SET translation_status = 'skipped' WHERE id = %s", (lid,))
            conn.commit()
            continue

        lang = detect_language(desc) if desc else (orig_lang or "ru")
        if lang != orig_lang:
            print(f"  [{i+1}/{len(rows)}] {lid[:8]}... re-detected: {orig_lang}→{lang}")

        targets = get_targets(lang)

        try:
            for target in targets:
                existing = desc_ru if target == "ru" else desc_uz
                if existing:
                    continue

                prompt = TRANSLATE_PROMPT.format(
                    source_lang=LANG_NAMES[lang],
                    target_lang=LANG_NAMES[target],
                    description=desc,
                    address=addr,
                )
                translated = call_translation_llm(prompt, provider=provider)

                updates = []
                params = []

                if translated.get("description"):
                    updates.append(f"description_{target} = %s")
                    params.append(translated["description"])
                if translated.get("address"):
                    updates.append(f"address_{target} = %s")
                    params.append(translated["address"])

                if lang in ("ru", "uz"):
                    orig_col = f"description_{lang}"
                    orig_val = desc_ru if lang == "ru" else desc_uz
                    if not orig_val and desc:
                        updates.append(f"{orig_col} = %s")
                        params.append(desc)
                    addr_col = f"address_{lang}"
                    updates.append(f"{addr_col} = COALESCE({addr_col}, %s)")
                    params.append(addr)

                if updates:
                    updates.append("translation_status = 'completed'")
                    updates.append("translated_at = NOW()")
                    updates.append("original_language = %s")
                    params.append(lang)
                    params.append(lid)
                    cur.execute(f"UPDATE {table} SET {', '.join(updates)} WHERE id = %s", params)

            conn.commit()
            success += 1
            print(f"  [{i+1}/{len(rows)}] {lid[:8]}... {lang}→{','.join(targets)} OK")

        except Exception as e:
            conn.rollback()
            failed += 1
            print(f"  [{i+1}/{len(rows)}] {lid[:8]}... FAILED: {e}")
            cur.execute(f"UPDATE {table} SET translation_status = 'failed' WHERE id = %s", (lid,))
            conn.commit()

        time.sleep(0.3)

    print(f"\n{table}: {success} translated, {failed} failed")
    return success, failed


def main():
    parser = argparse.ArgumentParser(description="Run pending listing translations")
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini", "ollama"],
        default=None,
        help="LLM provider to use (default: TRANSLATION_PROVIDER from .env)",
    )
    args = parser.parse_args()

    provider = args.provider or settings.translation_provider
    print(f"Translation provider: {provider}")

    conn = psycopg2.connect(**DB_PARAMS)

    total_success = 0
    total_failed = 0

    for table in ["olx_listings", "telegram_listings", "listings"]:
        s, f = process_table(conn, table, provider)
        total_success += s
        total_failed += f

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_success} translated, {total_failed} failed")
    print(f"{'='*60}")

    cur = conn.cursor()
    for table in ["olx_listings", "telegram_listings", "listings"]:
        cur.execute(f"SELECT translation_status, COUNT(*) FROM {table} GROUP BY translation_status")
        rows = cur.fetchall()
        print(f"\n{table}:")
        for row in rows:
            print(f"  {row[0]}: {row[1]}")

    conn.close()


if __name__ == "__main__":
    main()
