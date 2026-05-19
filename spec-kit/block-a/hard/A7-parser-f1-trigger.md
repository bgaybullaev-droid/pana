# A7 — Parser quality + F1 trigger

**Status:** PARTIAL — extraction + raw_text storage + Uzbek vocab + signature dedup are real; F1 generation pipeline (status enum, queue, Celery task, B2C visibility gating, junk filter, per-source metrics) is greenfield.
**Complexity:** HARD — touches the crawler, the backend ingest API, a new Celery task chain, model schema, B2C feed query, and admin observability. Multiple subsystems, multiple file boundaries.
**Block-A V2.0 ref:** A7 (Section "A7. Доработка качества парсера", Ф-10, Ф-11). The V2.0 reframing of A7 — "parser owns params + raw text only; AI owns display description" — is the central architectural shift across Block A.
**Vision-doc refs:** Ф-10, Ф-11. Block F (F1 = AI generation) is a hard prerequisite for half of this spec.
**Why now:** Every other Block-A task either depends on this directly (A1 description display, A4 push card body) or is unblocked by it (A8 admin metrics surface).

## What's done

- **LLM extraction** — `telegram-ai/crawler/llm_extractor.py` (Gemini-backed) extracts price, district, rooms, area, floor, total_floors, building_type, condition, amenities, deal_type. Prompt explicitly mentions Uzbek vocab `xonadon` (line 217), `sotiladi` / `ijaraga` (220, 449), `qavat` (226), `xona`, `xonali`. Prompt accepts both Cyrillic and Latin Uzbek (419-420).
- **Currency handling** — UZS, USD, "у.е.", `mln`, `k`, range pricing (`30-35 тыс.`) all handled at `llm_extractor.py:1119-1145`.
- **District normalisation** — Latin canonical names; matrix at `llm_extractor.py:511-541`.
- **Sotka conversion** — `1 sotka = 100 m²` handled at lines 488-496.
- **Raw source text persistence** — `TelegramListing.raw_text` at `backend/app/db/models.py:1315`, `OLXListing.raw_text` at `models.py:1434`. Crawler populates from `text` field (`FlexibleCrawlerWithHistory.py:227`); push payload includes it (`backend_push.py:77`).
- **Signature dedup** — `crawler_service.py:108-173`. Composite key: `normalized_phone + normalized_address + price + rooms + area`. Enforced at import: duplicate ⇒ marked dupe, not re-inserted.
- **ChromaDB exploratory dedup** — `vector_db.py:78-189` text + image embedding similarity (0.92 / 0.88 thresholds). Used for fuzzy match exploration; not the enforcement path.
- **Failure isolation per channel** — `FlexibleCrawlerWithHistory.py:301` continues on error.

## What's missing

1. **`pending_generation` / `generation_failed` statuses do not exist.** `ListingStatus` enum at `backend/app/db/models.py:65-72` is `ACTIVE / PAUSED / SOLD / DELETED / EXPIRED`. Without these, B2C visibility cannot gate on AI completion.
2. **AI generation queue does not exist.** `backend/app/workers/tasks/parser.py` literally contains `# TODO: CRIT-01 - AI Parser implementation` at lines 17-35. The translation Celery task (`celery_app.py:62`) is for i18n strings, not listing description generation.
3. **No `ai_description` columns.** `Listing` has `description` (today filled with raw text on crawler import), but no `ai_description_uz`, `ai_description_uz_lat`, `ai_description_ru` triplet.
4. **B2C feed does not gate on generation status.** `crawler/telegram/listings` at `backend/app/api/v1/crawler_import.py:69-116` and the buyer feed at `listings.py:1186-1188` filter on `ListingStatus.ACTIVE` and `ModerationStatus.APPROVED`. No `pending_generation`, no `unconfirmed`, no exclusion of partially-extracted listings.
5. **Signature dedup is missing `floor`.** Spec: `phone + area + floor + price ±5%`. Today: `phone + address + price + rooms + area`. Address is not in the spec (and isn't always reliably extracted), floor is in the spec and is reliably extracted.
6. **Junk filter is generic.** `llm_extractor.py:243-276` has `SKIP_PATTERNS` ("подписывайтесь", "реклама") but no rule for "куплю" (buying intent), "услуги" (services), "ремонт" (renovation services). Junk lands in the queue, wastes F1 calls, and pollutes the feed.
7. **No `unconfirmed` short-circuit for low-extraction listings.** Spec: listings missing any of `{deal_type, price, district}` stay `unconfirmed`, hidden from B2C, visible to admin. Today the import endpoint accepts and inserts whatever it gets; the buyer feed shows whatever has `ACTIVE + APPROVED`.
8. **No per-source quality metrics persisted.** `FlexibleCrawlerWithHistory.py:304-310` prints "Success: N / Failed: M" to stdout; no DB writes, no admin dashboard. ([A8](../medium/A8-channels-management.md) defines the storage; this spec defines what to write.)
9. **Long-text truncation for F1 prompt.** Spec: 3-5k character Telegram posts must be truncated to ~1500-2000 characters when fed into F1. F1 doesn't exist yet; no consumer to truncate for.
10. **Edit-time regeneration trigger.** Spec: when a realtor edits a key parameter (type, district, price, area, rooms), F1 must regenerate. Today the listings update endpoint does not enqueue anything.

## Path to DONE

Order is critical: data-model and queue first; observability and quality refinements after.

### Step 1 — extend `ListingStatus` and `Listing`

Migration:
- Add `ListingStatus.PENDING_GENERATION`, `ListingStatus.GENERATION_FAILED`, `ListingStatus.UNCONFIRMED`.
- Add columns: `Listing.ai_description_ru`, `Listing.ai_description_uz`, `Listing.ai_description_uz_lat` (TEXT, nullable). Keep `Listing.description` for backwards compat during migration; deprecate after F1 stabilises.
- Backfill: existing listings get `status=ACTIVE` unchanged.

### Step 2 — Stand up the F1 Celery task (delegates to Block F)

This is the first integration point with Block F. The skeleton:

```python
# backend/app/workers/tasks/ai_generation.py
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def generate_listing_description(self, listing_id: str):
    listing = _load(listing_id)
    if not listing.has_min_required_fields():  # deal_type, price, district
        listing.status = ListingStatus.UNCONFIRMED
        return
    try:
        prompt = build_prompt(listing, raw_text=listing.raw_text[:2000])
        result = call_gemini(prompt)
        listing.ai_description_ru = result.ru
        listing.ai_description_uz = result.uz
        listing.ai_description_uz_lat = result.uz_lat
        listing.status = ListingStatus.ACTIVE
    except RetryableError:
        raise self.retry(exc=...)
    except Exception:
        listing.status = ListingStatus.GENERATION_FAILED
        listing.ai_description_ru = build_template(listing, lang="ru")
        listing.ai_description_uz = build_template(listing, lang="uz")
        listing.ai_description_uz_lat = build_template(listing, lang="uz-latn")
```

Detailed F1 design lives in Block F. This spec only requires the trigger surface and the status-flip behaviour.

### Step 3 — Trigger F1 on import

In the crawler import endpoint (`backend/app/api/v1/crawler_import.py`), after a successful `Listing` insert:

```python
listing.status = ListingStatus.PENDING_GENERATION
db.commit()
generate_listing_description.delay(listing.id)
```

If `has_min_required_fields()` returns `False`, set `status=UNCONFIRMED` and skip the enqueue.

### Step 4 — Gate B2C feed

Two query sites:
- Buyer feed at `backend/app/api/v1/listings.py:1186-1188`: add `Listing.status == ListingStatus.ACTIVE` (not `IN(ACTIVE, PENDING_GENERATION, …)`); explicitly exclude `UNCONFIRMED`, `PENDING_GENERATION`. `GENERATION_FAILED` is debatable: spec says these still show with template description, so keep them in. Recommend: include `ACTIVE` + `GENERATION_FAILED`.
- Single-listing endpoint: same predicate.

Admin endpoints continue to see all statuses (existing pattern).

### Step 5 — Fix dedup signature

`crawler_service.py:108-173`: change the signature from `phone + address + price + rooms + area` to `phone + area + floor + price` with a ±5% price tolerance. `floor` is reliably extracted; `address` is not.

```python
def signature(listing) -> str:
    price_bucket = round(listing.price / max(listing.price * 0.05, 1))  # ±5% bucket
    return f"{listing.phone[-9:]}|{listing.area_sqm}|{listing.floor}|{price_bucket}"
```

### Step 6 — Junk filter

`llm_extractor.py:243-276`: extend `SKIP_PATTERNS` with `"куплю"`, `"услуги риелтора"`, `"ремонт квартир"`, plus their Uzbek equivalents (`"sotib olaman"`, `"xizmat"`). Add a positive-list check: a post matched by `SKIP_PATTERNS` is dropped before the LLM call.

### Step 7 — `unconfirmed` short-circuit

In `crawler_service.py` (the import path), before `db.add(listing)`:

```python
if not (listing.deal_type and listing.price and listing.district):
    listing.status = ListingStatus.UNCONFIRMED
    db.add(listing)
    return  # do not enqueue F1, do not surface to B2C
```

### Step 8 — Per-source metrics writeback

Crawler writes a `source_metric` row per source per day (storage defined in [A8](../medium/A8-channels-management.md)). Counters: `listings_found, listings_extracted, listings_failed, dupes_filtered, ai_failed`. Where `FlexibleCrawlerWithHistory.py:304-310` currently prints, POST instead.

### Step 9 — Edit-time regeneration

In the listing update endpoint, when one of `{deal_type, price, district, area_sqm, rooms}` changes, set `status=PENDING_GENERATION` and call `generate_listing_description.delay(listing.id)`. Block F2 will gate this on user confirmation; until F2 lands, regenerate eagerly.

### Step 10 — Long-text truncation

Trivial; in `build_prompt()` (Step 2), `raw_text[:2000]`.

## Behaviour & invariants

- **Parser writes structured params + raw_text + source metadata.** Nothing else. Description population is F1's responsibility.
- **B2C never sees raw_text.** Even when `status=GENERATION_FAILED`, the user sees the template description, not the raw text.
- **`Listing.raw_text` is preserved forever** — never cleared after generation; serves as F1 input + realtor "Show source" reference.
- **Listings missing any of `{deal_type, price, district}` are `UNCONFIRMED`** — invisible to B2C, visible to admin queues.
- **Dedup signature includes floor.** Address is too noisy; floor is reliable.
- **Junk filter runs before the LLM call** to save spend; matched posts never reach Gemini.
- **F1 idempotency** — re-running `generate_listing_description` on the same listing overwrites `ai_description_*`. Re-imports do not duplicate.
- **Per-source metrics writeback is best-effort** — crawler does not block on metric POST failure.

## Acceptance criteria

- Migration deploys; `ListingStatus` enum has `PENDING_GENERATION`, `GENERATION_FAILED`, `UNCONFIRMED`.
- New crawler import for a complete listing ⇒ `status=PENDING_GENERATION`, F1 task enqueued; after F1 success ⇒ `status=ACTIVE` and three `ai_description_*` populated; on permanent failure ⇒ `status=GENERATION_FAILED` with template descriptions.
- New crawler import missing `{deal_type, price, district}` ⇒ `status=UNCONFIRMED`; no F1 enqueue; not in B2C feed.
- Buyer feed query returns no `PENDING_GENERATION` or `UNCONFIRMED` rows.
- Two listings differing only in address but matching on `phone + area + floor + price ±5%` are deduped (one wins).
- A "куплю срочно квартиру" post is filtered before reaching Gemini.
- A 5000-char Telegram post is truncated to 2000 chars before F1 prompt.
- Per-source metrics row written daily for each active source.
- Editing one of {deal_type, price, district, area_sqm, rooms} on a `Listing` flips it to `PENDING_GENERATION` and re-enqueues F1.
- Spot-check on a 50-listing sample: ≥ 90% price extraction, ≥ 85% district, ≥ 95% rooms, ≥ 95% deal_type, ≥ 90% area, ≤ 10% visible duplicates in the feed.

## References

- `telegram-ai/crawler/FlexibleCrawlerWithHistory.py:227, 267-330` — raw_text capture, crawl loop.
- `telegram-ai/crawler/llm_extractor.py:215-276, 419-420, 488-541, 1119-1155` — LLM prompt, Uzbek vocab, currency, district, validation.
- `telegram-ai/crawler/schemas/real_estate.yaml` — schema (extracted fields).
- `telegram-ai/crawler/backend_push.py:44-206` — push payload.
- `telegram-ai/crawler/vector_db.py:78-189` — exploratory dedup (not enforcement).
- `backend/app/services/crawler_service.py:108-173` — signature dedup (modify).
- `backend/app/api/v1/crawler_import.py:69-116` — import + status flip.
- `backend/app/api/v1/listings.py:1186-1188` — buyer feed query (gate on status).
- `backend/app/db/models.py:65-72, 306-520` — ListingStatus + Listing model (extend).
- `backend/app/workers/tasks/parser.py:17-35` — placeholder for F1 task.
- `backend/app/workers/celery_app.py:13-19` — task registration.
- [A1 medium](../medium/A1-claim-reject-v2.md), [A4 hard](./A4-push-notifications.md), [A8 medium](../medium/A8-channels-management.md) — direct downstream consumers.
- Block F1 (out of scope for Block A spec-kit) — owns the actual generation prompt and quality.
