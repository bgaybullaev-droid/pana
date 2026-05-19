# A1 — Claim / Reject in Found (V2.0 deltas)

**Status:** PARTIAL — backend, migration, and frontend buttons are real and shipped; V2.0-specific deltas (raw-text passthrough, Master-record AI text, double-click guard) remain.
**Complexity:** MEDIUM — the backend skeleton is done, but the V2.0 framing introduces F1-coupling work (AI description, "Show source" block, pending-generation skeleton).
**Block-A V2.0 ref:** A1 (Section "A1. Завершить claim/reject в разделе Found").
**Vision-doc refs:** Ф-105, Ф-106, Ф-108. Supersedes the V1 partial spec at [`../../partial/medium/04-claim-flow.md`](../../partial/medium/04-claim-flow.md) (the reject endpoint listed as missing there is now done).
**Why now:** This is the first screen a registered seller sees; the V2.0 framing replaces the user-visible description with AI text, which is the difference between "system shows my exact words" and "system shows a polished card I'd happily approve".

## What's done

- **Three endpoints in `backend/app/api/v1/listings.py`:**
  - `POST /listings/claim-olx/{id}` (line 2195)
  - `POST /listings/claim-telegram/{id}` (line 2407)
  - `POST /listings/reject-crawled/{source}/{id}` (line 2506)
  All three: rate-limited (5/day, Redis), `SELECT FOR UPDATE` lock on the source row, audit-log entry, idempotent on retry.
- **Migration `20260426_prd_crawled_claim_reject.py`** — adds `converted_listing_id` (telegram_listings, unique partial idx), `rejected_by_seller_id` + `rejected_at` (both source tables, indexed).
- **Master-record creation** — `convert_olx_to_listing()` (`backend/app/services/crawler_service.py:514`) and `convert_telegram_to_listing()` (`crawler_service.py:591`) build a new `Listing` row with `source_type=SourceType.CLAIMED`, `status=ListingStatus.ACTIVE`, `moderation_status=ModerationStatus.APPROVED`, FK back via `converted_listing_id`. Seller's `listings_count` is incremented in the same transaction.
- **Per-realtor reject persistence** — `rejected_by_seller_id` is set on reject; `seller_crawled_listings.py` filters `rejected_by_seller_id IS NULL` so the same row doesn't reappear in `/sellers/me/crawled/{olx,telegram}`.
- **Frontend wiring** — `frontend/src/modules/seller/pages/found/ui/page/Page.tsx:210-258` calls the real endpoints via `frontend/src/modules/seller/shared/api/sellerCrawledListings.ts:51-75`; cards optimistically removed; error toasts on failure.
- **Master-record ranking boost** — see [`../../partial/easy/F108-master-record-ranking.md`](../../partial/easy/F108-master-record-ranking.md); separate spec.

## What's missing (V2.0)

1. **Raw source text not copied on claim.** Both `TelegramListing.raw_text` (`backend/app/db/models.py:1315`) and `OLXListing.raw_text` (`models.py:1434`) hold the original post body. `Listing.raw_text` exists at `models.py:490` but the `convert_*_to_listing()` functions leave it `NULL`. Without the copy, the V2.0 "Show source" collapsible (the only way the realtor sees their own original wording) cannot be built.
2. **AI-description plumbing absent.** `Listing` has no `ai_description` (or equivalent), no `ai_description_uz`, `_ru`, `_uz_lat` triplet, no `pending_generation` / `generation_failed` status. The `ListingStatus` enum at `models.py:65-72` is ACTIVE / PAUSED / SOLD / DELETED / EXPIRED. Hard-blocked by F1 — see [A7 hard spec](../hard/A7-parser-f1-trigger.md) for the prerequisite work.
3. **`Listing.description` is sourced directly from crawler text** during claim (`crawler_service.py:514-663`), so claimed listings render the realtor's raw post in B2C — the exact behaviour V2.0 outlaws.
4. **Frontend double-click race** — buttons in `Page.tsx:754-767` rely on optimistic removal but have no `disabled` state during the in-flight request. Backend's `SELECT FOR UPDATE` saves correctness but the UI lets the user fire two requests in a row, which produces a confusing toast pair.
5. **No "Show source" UI** — there's no collapsible block in `frontend/src/modules/seller/pages/listings/ui/page/Page.tsx` (or the listing-detail screen) that surfaces `raw_text`.
6. **No skeleton state for `pending_generation`** — when F1 lands, claimed listings will briefly have no AI text; the cabinet must render a skeleton instead of an empty description (spec edge case, A1).

## Path to DONE

Order matters: items 1 and 4 are pre-F1 quick wins; the rest gate on F1 from A7.

1. **Copy `raw_text` on convert.** In both `convert_olx_to_listing()` and `convert_telegram_to_listing()` (`crawler_service.py:514, 591`), set `Listing.raw_text = source.raw_text` before the `db.add(listing)` call. One line per function.
2. **Add a `disabled` state to the Found buttons.** Two places in `Page.tsx:754-767`. Use the existing `loading` boolean from the mutation hook, or local React state if the mutation is fire-and-forget. Keep it disabled until the mutation resolves (success or error).
3. **Add the "Show source" collapsible** (gated on `raw_text` non-null) to the seller listings page or the listing detail. Mantine `Collapse` + a `useDisclosure` hook is enough. Copy keys go through [A6 i18n](./A6-i18n-leaks.md): `seller.showSource`, `seller.hideSource`.
4. **Wait for F1 to land** ([A7](../hard/A7-parser-f1-trigger.md)). Once `pending_generation` and `ai_description` exist:
    - Replace the description used in B2C with the AI version (controller decides language by viewer locale).
    - Render a skeleton in the seller cabinet when `status === 'pending_generation'`.
    - Trigger F1 regeneration on major-param edit (covered by F2; this spec just needs to call the trigger).
5. **Already-claimed-by-other-seller branch** — backend currently 409s the second claim (locked row prevents the second insert from succeeding). Frontend toast copy: "this listing is already claimed by another account". Add to `Page.tsx` error handler at line 251.

## Behaviour & invariants

- **Claim is idempotent on retry.** `converted_listing_id` is unique-partial; second insert no-ops, returns existing master-record id.
- **Reject is permanent and per-seller.** Re-importing the same Telegram message (same `message_id`) does not clear `rejected_by_seller_id`. If the seller wants it back they must contact admin (out of MVP).
- **Anonymous parser-record stays alive after reject.** The crawler's `TelegramListing` / `OLXListing` row keeps existing and the Master record (if any) keeps showing in B2C; reject only suppresses it from the seller's Found list.
- **`Listing.raw_text` is realtor-only data.** Never returned in B2C feed responses; only on `/sellers/me/listings/*` when the requester owns the listing.
- **Double-click safety** — backend lock + frontend disabled state. Either alone is insufficient: backend lock prevents double-create, but without the disabled state the user sees two competing toasts.

## Acceptance criteria

- After claim, the new `Listing.raw_text` equals the source row's `raw_text` (verify via DB).
- Found page buttons are visibly disabled (greyed-out + non-interactive) for the duration of the in-flight request.
- "Показать исходный текст" / "Show source from origin" collapsible renders on a claimed listing's cabinet card; collapsed by default.
- (After F1 lands) Description shown in B2C is `Listing.ai_description_<locale>`, never `Listing.raw_text`.
- (After F1 lands) `status='pending_generation'` listings render a skeleton in cabinet; do not appear in B2C until generation completes.
- Re-claim of an already-claimed listing returns a 409 with a translated error toast: "Это объявление уже подтверждено другим аккаунтом".

## References

- `backend/app/api/v1/listings.py:2195, 2407, 2506` — claim/reject endpoints.
- `backend/app/services/crawler_service.py:514, 591` — `convert_*_to_listing` (where `raw_text` copy goes).
- `backend/app/db/models.py:65-72` — `ListingStatus` enum (needs F1 extension).
- `backend/app/db/models.py:490` — `Listing.raw_text` column (currently unused after claim).
- `backend/app/db/models.py:1315, 1434` — source raw text on TelegramListing / OLXListing.
- `backend/alembic/versions/20260426_prd_crawled_claim_reject.py` — claim/reject migration (shipped).
- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx:210-258, 754-767` — frontend handlers + buttons.
- `frontend/src/modules/seller/shared/api/sellerCrawledListings.ts:51-75` — API client.
- [A3](../easy/A3-mock-data-found.md), [A6](./A6-i18n-leaks.md), [A7](../hard/A7-parser-f1-trigger.md) — directly coupled.
