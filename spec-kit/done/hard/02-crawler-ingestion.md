# 02 — Crawler & Ingestion (Ф-10)

**Status:** DONE
**Complexity:** HARD — off-process Telethon + Playwright crawlers, LLM extraction pipeline, ChromaDB vector dedup, async translation, plus three coupled tables (TelegramListing / OLXListing / Listing).
**Vision-doc refs:** Ф-10 (parser engine), Section 3 (cold-start strategy)

## Summary

Off-process crawlers under `telegram-ai/` (Telethon → top-25 channels) and `telegram-ai/crawler-olx/` (Playwright → OLX.uz) scrape raw text, push it through an LLM extractor (Gemini / OpenAI configurable) to produce structured listings, dedup against ChromaDB, then import via REST into the main backend's crawler-import endpoints. Imports populate `TelegramListing` / `OLXListing` (raw) **and** the unified `Listing` table with `source_type=PARSED`.

## Components

| Component | Path | Role |
|---|---|---|
| Telegram crawler | `telegram-ai/crawler/` | Telethon session reads channels listed in `channels_config.yaml`. |
| OLX crawler | `telegram-ai/crawler-olx/` | Playwright page-walks OLX category pages. |
| LLM extractor | `telegram-ai/crawler/schemas/real_estate.yaml` + LLM provider | Maps free-form text → structured fields per schema. |
| Translator | `backend/app/workers/tasks/translation.py` | Async ru↔uz fill via OpenAI / Gemini. |
| Dedup | ChromaDB (vector signature) + SHA-style `signature_hash` on Listing. |
| Import API | `backend/app/api/v1/crawler_import.py` | Receives extracted batches; writes raw + unified rows. |
| Server / dashboard | `telegram-ai/api/server_sqlite.py`, `static/dashboard.*` | Operator UI for crawler health (out-of-band, SQLite). |

## Data model

`backend/app/db/models.py` — relevant tables:

- `Listing` (line 309) — unified canonical table. `source_type: SourceType` enum (`MANUAL` / `PARSED`), `source_url`, `source_channel`, `raw_text`, `signature_hash`, `master_record_id` FK to itself for dedup chains.
- `TelegramListing` (line ~1215) — raw Telegram-channel listings. Fields: `property_type`, `listing_type`, `price`, `currency`, `district`, `rooms`, `area`, `floor`, `phone`, `source_channel`, `message_id`, etc.
- `OLXListing` (line ~1300) — raw OLX listings. Same fields plus `source = 'olx_uz'`, `crawled_at`, `seller_type`, `views_count`.

## Import endpoints

Under `/api/v1/crawler/*`. Auth via shared secret (configured via env, not JWT).

- `POST /crawler/import/telegram` — batch insert TelegramListing + create / update Listing.
- `POST /crawler/import/olx` — same for OLX.
- The promotion path also runs the **dedup signature** task and queues the **Meilisearch index** task.

## Behaviour & invariants

- **`source_type=PARSED` always** for crawler-imported Listings. Manual creates use `MANUAL`.
- **Dedup** — `signature_hash` on Listing + ChromaDB nearest-neighbour. Duplicates set `master_record_id` to the canonical row.
- **Deactivation** — when a source URL stops returning a listing, the corresponding Listing transitions to `EXPIRED`.
- **Phone normalisation** — `app.utils.phone.normalize_phone` keeps the last 9 digits; downstream the claim flow matches sellers via `func.right(phone, 9)`.
- **Translation pipeline** — Celery `translate_listing` runs async after import; populates ru↔uz title/description.

## References

- `backend/app/services/crawler_service.py`
- `backend/app/services/seller_crawled_listings.py` (claim/found flow uses this)
- `backend/app/api/v1/crawler_import.py`
- `backend/app/api/v1/listings.py` — `feed` endpoint applies `master_record_id IS NULL` filter (canonical only).
- `telegram-ai/crawler/channels_config.yaml` — channel allowlist.
- `telegram-ai/crawler/schemas/real_estate.yaml` — extraction schema.

## Known gaps

- Master records don't yet rank above parsed siblings (just deduped). See `../../partial/easy/F108-master-record-ranking.md`.
- Crawler dashboard runs against SQLite, not the canonical Postgres — operator metrics are isolated from production.
