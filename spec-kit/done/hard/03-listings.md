# 03 — Listings & Images

**Status:** DONE
**Complexity:** HARD — visibility matrix evolved across 8 sprints with dual-read field aliases, image pipeline (local + optional S3) with cwd-independent serving, status state machine, Meilisearch sync.

## Summary

Single canonical `Listing` table holds both manual and crawler-sourced listings, gated by a per-property-type / per-listing-type "visibility matrix" (Sprints S1–S8 progressively added fields). Status pipeline drives moderation. Images live under `backend/uploads/...` (or S3 if configured) and are served via FastAPI `StaticFiles`. Feed is paginated, filtered, and ordered by boost.

## Data model

`backend/app/db/models.py:309` — `Listing`. Selected columns:

| Column | Notes |
|---|---|
| `id`, `seller_id` | Seller FK is nullable so crawled listings without a claimed seller can exist. |
| `type: ListingType` | `SELL` / `RENT`. |
| `property_type: PropertyType` | `APARTMENT` / `HOUSE` / `COMMERCIAL` / `LAND`. |
| `district`, `region`, `address` (S3) | Location. |
| `price`, `currency`, `price_per_sqm` (S4) | Money. |
| `rooms`, `area`, `floor`, `total_floors`, `ceiling_height` | Geometry. |
| `building_type`, `market_type`, `house_type`, `condition`, `wall_material`, `furniture` (S5) | Build info. (Sprint 5 introduced `market_type` + `furniture` as preferred names; legacy `building_type` + `is_furnished` still accepted by validators.) |
| `deed_type` (S2), `commercial_type` (S4), `land_purpose` | Categorical add-ons. |
| `garage`, `basement`, `listing_subtype`, `floor_plan_url` (S6) | Property polish. |
| `seller_type` (S7) | `owner` / `realtor`. |
| `is_boosted`, `boost_until` | Promotion flag. |
| `status: ListingStatus` | `DRAFT` / `ACTIVE` / `PENDING` / `REJECTED` / `EXPIRED` / `SOLD` / `INACTIVE`. |
| `views_count` | Incremented on detail open (see Notifications spec for view tracking semantics). |
| `source_type`, `source_url`, `raw_text`, `signature_hash`, `master_record_id` | See [02-crawler-ingestion](02-crawler-ingestion.md). |
| `created_at`, `updated_at`, `expires_at`, `claimed_at` | Lifecycle. |

`ListingImage` (line ~601) — UUID rows holding `original_url`, `thumbnail_url`, `medium_url`, `large_url`, `position`, `is_primary`. CASCADE on `listing_id`.

## API surface

`backend/app/api/v1/listings.py`.

| Verb | Path | Purpose |
|---|---|---|
| GET | `/listings/feed` | Paginated public feed; filters by type, property_type, district, price, rooms, etc. Two retrieval paths: a Meilisearch path for free-text queries (preserves Meili rank) and a default Postgres path. |
| GET | `/listings/{id}` | Detail; increments `views_count`. |
| POST | `/listings` | Seller create. Validator `_validate_required_fields` runs the matrix gate. |
| PATCH | `/listings/{id}` | Seller edit (or admin). |
| POST | `/listings/{id}/status` | Status transitions (pause/resume/sold/etc.). |
| POST | `/uploads` | Multipart image upload — see below. |

## Image pipeline

- **Upload** via `POST /uploads/listings/{listing_id}` (or generic). Files stored under `UPLOAD_DIR` (default `backend/uploads/`), filename = UUID + extension.
- **Static serving** — `app.main` mounts `/uploads` via `StaticFiles(directory=UPLOAD_DIR)`. The directory is resolved relative to the **backend package root** (`Path(__file__).resolve().parent.parent`) so it works regardless of process cwd. Absolute `settings.upload_dir` values are honoured as-is.
- **Garbage collection** — `backend/app/workers/tasks/uploads_gc.py` removes orphan files (no DB row points at them).
- **Optional S3** — env vars `AWS_ACCESS_KEY_ID`, `S3_BUCKET_NAME`, `CLOUDFRONT_DOMAIN`. When set, listing images are uploaded to S3 instead of local disk; the local path is still served as fallback.

## Behaviour & invariants

- **Visibility matrix** — `_validate_required_fields` rejects payloads missing required fields for the (property_type × listing_type) cell. The matrix expanded across Sprints S1–S8 (see migrations in `backend/alembic/versions/2026041*_s*.py`).
- **Dual-read S5 fields** — `(market_type OR building_type)` and `(furniture OR is_furnished)` both pass validation. Letters older clients keep working while new code writes the preferred name.
- **Feed ordering (Postgres path)** — `Listing.is_boosted DESC` then the requested `sort_by` (default `created_at DESC`). The query also gates on `status=ACTIVE`, `moderation_status=APPROVED`, `deleted_at IS NULL`. Meili path preserves Meili's relevance order.
- **No master-record dedup in feed.** The feed query does not filter `master_record_id IS NULL`, so duplicate parsed rows render alongside their master. Tracked in `../../partial/easy/F108-master-record-ranking.md`.
- **Auto-approve** — controlled by `settings.auto_approve_listings`. When true, manual listings skip `PENDING` and land in `ACTIVE`.
- **Search backend** — Meilisearch (`MEILISEARCH_HOST`); `app.workers.tasks.listings.sync_to_meilisearch` keeps the index in sync.
- **Currency** — `currency: ListingCurrency` on each row. `EXCHANGE_RATE_API_URL` and `EXCHANGE_RATE_FALLBACK` drive cross-currency display logic on the frontend.

## References

- `backend/app/api/v1/listings.py` — router + validator.
- `backend/app/db/models.py:309` — Listing model.
- `backend/app/workers/tasks/listings.py` — index, expire, dedup tasks.
- `backend/app/main.py:48-55` — `UPLOAD_DIR` resolution; line 160 mount.
- `frontend/src/shared/ui/ListingCard.tsx` — public card.
- `frontend/src/modules/seller/pages/listings/` — seller portfolio + edit.

## Known gaps

- Sold-price capture not modelled (see `../../not-started/medium/deal-status-and-final-price.md`).
- **Master-record priority + dedup filter** not applied in feed: duplicates render and ranking has no claim-boost (see `../../partial/easy/F108-master-record-ranking.md`).
