#!/usr/bin/env python3
"""
Idempotent backfill script for English→Russian/Uzbek translations.

Finds listings where _uz or _ru columns contain English text instead
of proper translations, and translates them using OpenAI GPT-4o-mini.

Usage:
    python backend/scripts/backfill_translations.py [--dry-run]

    --dry-run   Show what would change without modifying the database
                or calling the translation API.

Requires: psycopg2-binary, openai
"""

import argparse
import json
import logging
import os
import re
import sys
import time

import psycopg2

# ── Configuration ────────────────────────────────────────────────────
DB_HOST = "192.168.0.189"
DB_PORT = 5432
DB_USER = "postgres"
DB_PASS = "web@1234"
DB_NAME = "real_estate"

# Read OpenAI key from .env or environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    OPENAI_API_KEY = line.split("=", 1)[1].strip()
                    break

MIN_TEXT_LENGTH = 5  # Skip very short/gibberish content

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


# ── Language detection ───────────────────────────────────────────────

def is_english(text: str) -> bool:
    """Detect if text is predominantly English (Latin, no Cyrillic)."""
    if not text or text.strip() in ("None", ""):
        return False
    cyrillic = len(re.findall(r"[\u0400-\u04FF]", text))
    latin = len(re.findall(r"[a-zA-Z]", text))
    total = cyrillic + latin
    if total < 3:
        return False
    return latin / total > 0.7 and cyrillic == 0


def is_gibberish(text: str) -> bool:
    """Detect test/gibberish content that shouldn't be translated."""
    if not text or len(text.strip()) < MIN_TEXT_LENGTH:
        return True
    clean = re.sub(r"[^a-zA-Z\s]", "", text.lower()).strip()
    if len(clean) < MIN_TEXT_LENGTH:
        return True
    # Random letter sequences with almost no vowels
    vowels = sum(1 for c in clean if c in "aeiou")
    if len(clean) > 5 and vowels / max(len(clean), 1) < 0.15:
        return True
    return False


# ── Translation via OpenAI ───────────────────────────────────────────

_TRANSLATE_PROMPT = (
    "Translate the following real estate listing fields from English to {target_lang}.\n"
    "Preserve proper nouns, landmark names, district names, street names, metro stations, "
    "measurements (m², sotka), and phone numbers exactly as-is.\n"
    "Return ONLY valid JSON with these keys (omit key if input is empty/null):\n"
    '{{"title": "...", "description": "...", "address": "..."}}\n\n'
    "Input:\n"
    "title: {title}\n"
    "description: {description}\n"
    "address: {address}"
)

_LANG_NAMES = {"ru": "Russian", "uz": "Uzbek"}


def translate_text(title: str, description: str, address: str, target_lang: str) -> dict:
    """Call OpenAI GPT-4o-mini to translate EN → target_lang."""
    import openai

    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    prompt = _TRANSLATE_PROMPT.format(
        target_lang=_LANG_NAMES[target_lang],
        title=title or "",
        description=description or "",
        address=address or "",
    )

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a real estate listing translator for Uzbekistan. "
                    "Translate accurately from English to "
                    f"{_LANG_NAMES[target_lang]}. "
                    "Return ONLY valid JSON, no markdown fences."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=2000,
    )
    text = resp.choices[0].message.content.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    return json.loads(text)


# ── Table configuration ──────────────────────────────────────────────

TABLES = {
    "listings": {
        "base_fields": ["title", "description", "address"],
        "lang_fields": {
            "ru": ["title_ru", "description_ru", "address_ru"],
            "uz": ["title_uz", "description_uz", "address_uz"],
        },
    },
    "telegram_listings": {
        "base_fields": ["description", "address"],
        "lang_fields": {
            "ru": ["description_ru", "address_ru"],
            "uz": ["description_uz", "address_uz"],
        },
    },
    "olx_listings": {
        "base_fields": ["description", "address"],
        "lang_fields": {
            "ru": ["description_ru", "address_ru"],
            "uz": ["description_uz", "address_uz"],
        },
    },
}


# ── Main backfill ────────────────────────────────────────────────────

def run_audit(cur) -> dict:
    """Count records needing translation."""
    stats = {}
    for table in TABLES:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        total = cur.fetchone()[0]
        stats[table] = {"total": total}
    return stats


def backfill(dry_run: bool = False):
    if not OPENAI_API_KEY and not dry_run:
        log.error("OPENAI_API_KEY not set. Cannot translate. Use --dry-run to preview.")
        sys.exit(1)

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )
    cur = conn.cursor()

    total_detected = 0
    total_translated_uz = 0
    total_translated_ru = 0
    total_skipped_gibberish = 0
    total_skipped_already = 0
    total_failed = 0

    for table, config in TABLES.items():
        base_fields = config["base_fields"]
        has_title = "title" in base_fields

        # Fetch all columns we need
        select_cols = ["id", "original_language", "translation_status"]
        select_cols += base_fields
        for lang_cols in config["lang_fields"].values():
            select_cols += lang_cols

        cur.execute(f"SELECT {', '.join(select_cols)} FROM {table}")
        rows = cur.fetchall()

        log.info(f"\n{'='*60}")
        log.info(f"  Processing {table} ({len(rows)} records)")
        log.info(f"{'='*60}")

        for row in rows:
            # Build dict from row
            d = dict(zip(select_cols, row))
            row_id = d["id"]

            # Get base field values
            title_val = str(d.get("title", "") or "")
            desc_val = str(d.get("description", "") or "")
            addr_val = str(d.get("address", "") or "")

            # Skip records already processed by this script
            # (original_language set to 'en' + translation_status 'completed')
            if d.get("original_language") == "en" and d.get("translation_status") == "completed":
                continue

            # Check if any base field has English content
            en_title = has_title and is_english(title_val)
            en_desc = is_english(desc_val)
            en_addr = is_english(addr_val)

            if not en_title and not en_desc and not en_addr:
                continue  # No English content

            total_detected += 1

            # Skip gibberish
            all_gibberish = True
            for val, is_en in [(title_val, en_title), (desc_val, en_desc), (addr_val, en_addr)]:
                if is_en and not is_gibberish(val):
                    all_gibberish = False
                    break

            if all_gibberish:
                log.info(f"  [SKIP GIBBERISH] {row_id}: \"{(title_val or desc_val)[:50]}\"")
                total_skipped_gibberish += 1
                continue

            # Check which languages need translation
            needs = {}  # lang -> True
            for lang, lang_cols in config["lang_fields"].items():
                # Check if any _lang column still contains English
                any_english_in_lang = False
                all_present = True
                for lc in lang_cols:
                    lv = str(d.get(lc, "") or "")
                    if not lv or lv.strip() in ("", "None"):
                        all_present = False
                    elif is_english(lv):
                        any_english_in_lang = True

                if any_english_in_lang or not all_present:
                    needs[lang] = True

            if not needs:
                total_skipped_already += 1
                continue

            log.info(f"  [{row_id}] needs: {list(needs.keys())}")
            log.info(f"    title: \"{title_val[:60]}\"" if has_title else "")
            log.info(f"    desc:  \"{desc_val[:60]}\"")
            log.info(f"    addr:  \"{addr_val[:40]}\"")

            for lang in needs:
                if dry_run:
                    log.info(f"    -> [DRY RUN] would translate EN→{lang.upper()}")
                    if lang == "uz":
                        total_translated_uz += 1
                    else:
                        total_translated_ru += 1
                    continue

                try:
                    translated = translate_text(
                        title=title_val if en_title else "",
                        description=desc_val if en_desc else "",
                        address=addr_val if en_addr else "",
                        target_lang=lang,
                    )

                    # Build UPDATE
                    updates = []
                    params = []

                    if has_title and translated.get("title"):
                        updates.append(f"title_{lang} = %s")
                        params.append(translated["title"][:200])
                    if translated.get("description"):
                        updates.append(f"description_{lang} = %s")
                        params.append(translated["description"])
                    if translated.get("address"):
                        updates.append(f"address_{lang} = %s")
                        params.append(translated["address"][:500])

                    if updates:
                        # Also fix original_language and translation_status
                        updates.append("original_language = 'en'")
                        updates.append("translation_status = 'completed'")

                        sql = f"UPDATE {table} SET {', '.join(updates)} WHERE id = %s"
                        params.append(row_id)
                        cur.execute(sql, params)

                        log.info(f"    -> EN→{lang.upper()} done: "
                                 f"title={'yes' if translated.get('title') else 'n/a'}, "
                                 f"desc={'yes' if translated.get('description') else 'n/a'}, "
                                 f"addr={'yes' if translated.get('address') else 'n/a'}")

                        if lang == "uz":
                            total_translated_uz += 1
                        else:
                            total_translated_ru += 1

                    # Rate limit: avoid hitting OpenAI too fast
                    time.sleep(0.3)

                except Exception as e:
                    log.error(f"    -> EN→{lang.upper()} FAILED: {e}")
                    total_failed += 1

    if not dry_run:
        conn.commit()
        log.info("\n  ** Changes committed **")
    else:
        conn.rollback()
        log.info("\n  ** DRY RUN — no changes made, no API calls **")

    # ── Post-audit: count remaining English ──
    remaining_en = 0
    if not dry_run:
        for table, config in TABLES.items():
            base_fields = config["base_fields"]
            select_cols = ["id"] + base_fields
            for lang_cols in config["lang_fields"].values():
                select_cols += lang_cols
            cur.execute(f"SELECT {', '.join(select_cols)} FROM {table}")
            for row in cur.fetchall():
                d = dict(zip(select_cols, row))
                for lang_cols in config["lang_fields"].values():
                    for lc in lang_cols:
                        lv = str(d.get(lc, "") or "")
                        if is_english(lv) and not is_gibberish(lv):
                            remaining_en += 1
                            break
                    else:
                        continue
                    break

    log.info(f"\n{'='*60}")
    log.info(f"  SUMMARY")
    log.info(f"{'='*60}")
    log.info(f"  Total English records detected:   {total_detected}")
    log.info(f"  UZ translations created:          {total_translated_uz}")
    log.info(f"  RU translations created:          {total_translated_ru}")
    log.info(f"  Skipped (gibberish):              {total_skipped_gibberish}")
    log.info(f"  Skipped (already translated):     {total_skipped_already}")
    log.info(f"  Failed:                           {total_failed}")
    if not dry_run:
        log.info(f"  Remaining English-only rows:      {remaining_en}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill English→RU/UZ translations")
    parser.add_argument("--dry-run", action="store_true", help="Preview without changes or API calls")
    args = parser.parse_args()

    backfill(dry_run=args.dry_run)
