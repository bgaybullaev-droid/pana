# 04 — Claim Flow (Ф-105 / Ф-106)

**Status:** PARTIAL — initiate + verify ship end-to-end; **reject endpoint missing** despite the rejection-tracking migration having landed.
**Complexity:** MEDIUM — two clean paths (auto-verify on phone match + OTP fallback), bounded scope; the gap is one endpoint + its frontend wiring.
**Vision-doc refs:** Section 3.2 (hybrid model), Section 5.1 ("Уровень 1" — claim-флоу).

## What's done

When a seller registers, the system surfaces every crawler-imported listing whose phone matches the seller's via the **crawled-listings endpoints** (not a single `/sellers/me/found` route as originally documented):

- `GET /sellers/me/crawled/stats` — aggregate counts.
- `GET /sellers/me/crawled/olx` — paginated OLX matches.
- `GET /sellers/me/crawled/telegram` — paginated Telegram-channel matches.

The seller taps **Это моё** → `POST /claims/` initiates a claim. If `seller.phone` matches `listing.phone` (last-9-digit suffix), the claim is auto-verified in one DB transaction (`status=VERIFIED`, `Listing.seller_id` reassigned, `Listing.claimed_at` stamped). Otherwise, a `PENDING` claim is created and a 6-digit OTP is sent through the bot. `POST /claims/{claim_id}/verify` redeems the OTP (3-attempt cap, 10-minute TTL, daily ceiling `MAX_CLAIMS_PER_DAY=5`).

`GET /claims/{claim_id}` returns status for polling.

## Data model

`backend/app/db/models.py:643` — `ListingClaim`.

| Column | Notes |
|---|---|
| `id` | UUID. |
| `listing_id`, `seller_id` | FKs (CASCADE). |
| `status` | `PENDING` / `VERIFIED` / `REJECTED` / `EXPIRED`. |
| `verification_otp`, `otp_expires_at`, `verification_attempts` | OTP gate. |
| `created_at`, `verified_at`, `rejected_at` | Lifecycle. |

`backend/alembic/versions/20260426_prd_crawled_claim_reject.py` adds **per-seller rejection tracking** (the table the missing endpoint should write to).

## API surface — actual

`backend/app/api/v1/claims.py`:

| Verb | Path | Purpose |
|---|---|---|
| POST | `/claims/` | Initiate. Body `{listing_id}`. Auto-verifies on phone match; otherwise creates `PENDING` and OTPs. |
| POST | `/claims/{claim_id}/verify` | Redeem OTP. |
| GET | `/claims/{claim_id}` | Status check. |

`backend/app/api/v1/sellers.py` (Found list lives here, not on `/claims/`):

| Verb | Path | Purpose |
|---|---|---|
| GET | `/sellers/me/crawled/stats` | Aggregate counts. |
| GET | `/sellers/me/crawled/olx` | Paginated OLX matches. |
| GET | `/sellers/me/crawled/telegram` | Paginated Telegram matches. |

## Gap — what's missing

1. **`POST /claims/{id}/reject`** (or `POST /claims/reject` with `{listing_id}`) — writes a row in the per-seller-rejection table the migration introduced, so the listing stops appearing in `/sellers/me/crawled/...` for this seller. **Not implemented.**
2. **Frontend reject button wiring** — the Found page presumably has a "Не моё" button; without the endpoint it either errors or is dead. Verify and either disable until the endpoint ships or remove if never wired.
3. **`# TODO: Send OTP via SMS`** comment in `claims.py` is misleading — OTP is delivered via the Telegram bot today, which is correct for the WebApp flow. Either remove the TODO or scope a separate spec for an SMS fallback for sellers without a linked Telegram.

## Behaviour & invariants (the parts that ARE done)

- **Phone-suffix match** uses `app.utils.phone.normalize_phone(...)` (last 9 digits) — country-code differences don't break matching.
- **Auto-verify** — claim row created with `status=VERIFIED` directly in the same transaction as the seller-id reassignment.
- **OTP path** — 6-digit code, 10-min TTL, 3-attempt cap, sent via `get_bot_instance().send_message(chat_id=user.telegram_id, ...)`.
- **Daily cap** — `MAX_CLAIMS_PER_DAY=5` enforced via Redis counter.
- **Master-record candidacy** — `Listing.claimed_at` is stamped on success. Promotion-over-duplicates is a separate ranking concern (see `../easy/F108-master-record-ranking.md`).

## Frontend

`frontend/src/modules/seller/pages/found/ui/page/Page.tsx` calls `/sellers/me/crawled/...` to fetch and `/claims/` to initiate. API client at `frontend/src/modules/seller/shared/api/sellerCrawledListings.ts`.

## References

- `backend/app/api/v1/claims.py`
- `backend/app/api/v1/sellers.py` — Found-list endpoints.
- `backend/app/services/seller_crawled_listings.py` — match logic.
- `backend/app/db/models.py:643` — `ListingClaim`.
- `backend/alembic/versions/20260426_prd_crawled_claim_reject.py` — reject schema (no endpoint).
- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx`

## Path to DONE

1. Add `POST /claims/{id}/reject` (or `/claims/reject` with `{listing_id}`); writes the rejection row, returns 200.
2. Frontend: wire the existing reject button to the new endpoint with optimistic-remove.
3. Remove the `# TODO: Send OTP via SMS` comment in `claims.py` (or open a follow-up spec for SMS fallback).
4. After (1)-(3), promote this spec back to `done/medium/04-claim-flow.md`.

## Known gaps adjacent to this spec

- **Ф-107 (notify seller when a new crawled listing matches their phone)** is not implemented — `/sellers/me/crawled/*` is pull-only. See `../../not-started/medium/F107-seller-claim-notification.md`.
