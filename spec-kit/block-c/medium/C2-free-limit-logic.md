# C2 — Free-listing limit logic (info-only during test period)

**Status:** NOT STARTED — `Seller.listings_count` exists from Block A but is **not status-aware**, no quota middleware, no per-status badge in UI.
**Complexity:** MEDIUM — counter cleanup is small; the architecture work (feature-flag-gated middleware that's testable but never fires in test period) is the careful piece.
**Block-C V2.0 ref:** C2.
**Why now:** if the counter is broken when monetization activates, billing will be wrong on day-1. We have to get the count right *now* even though enforcement comes later.

## What's done

- **`Seller.listings_count`** denormalised counter exists at `backend/app/db/models.py:298`.
- **Increment hooks** at every creation site:
  - `backend/app/api/v1/listings.py:2849` — `seller.listings_count += 1` on POST `/listings`.
  - `backend/app/api/v1/claims.py:113, 232` — claim flow.
  - `backend/app/services/crawler_service.py:608, 685` — `convert_olx_to_listing`, `convert_telegram_to_listing` (post-claim conversion).
- **Decrement hook** at one site:
  - `backend/app/api/v1/listings.py:3200` — `seller.listings_count = max(0, seller.listings_count - 1)` on soft-delete.
- **Status enum** post-A7 has the full set: `ACTIVE / PAUSED / SOLD / DELETED / EXPIRED / PENDING_GENERATION / GENERATION_FAILED / UNCONFIRMED` (`models.py:65-85`).
- **Listing PATCH endpoint** at `listings.py:3016` that sets `listing.status` from a string value — but does NOT update `seller.listings_count` on transitions like ACTIVE→PAUSED.

## What's missing

1. **Counter is not status-aware.** PAUSED, SOLD, EXPIRED, ARCHIVED, GENERATION_FAILED, UNCONFIRMED, PENDING_GENERATION listings all currently inflate `listings_count`. Spec defines "active" strictly as `status=ACTIVE`. **The current count is wrong for billing and for display.**
2. **Status transitions don't update the counter.** Pausing a listing should drop the active count; un-pausing should bump it. Today neither happens.
3. **No `active_listings_count` field** distinct from a "lifetime listings" or "all non-deleted" sense. Today the field tries to be both and lands neither.
4. **No quota-checking middleware / dependency** at the create-listing endpoint. POST `/listings` and POST `/listings/claim-{olx,telegram}` accept unconditionally.
5. **No per-status breakdown on `/sellers/me/dashboard`.** It exposes `total_listings` only (`sellers.py:549-634`).
6. **No "X active" header chip** on the seller "My Listings" page (`seller/pages/listings/ui/page/Page.tsx`).
7. **No info-toast / banner on listing-create** when a seller publishes their 3rd-or-later listing.
8. **No feature flag.** Even if the spec says "no blocking during test period", architecture should be ready for the flag flip — no flag exists.

## Path to DONE

### Step 1 — define the source of truth

Two options. **Recommendation: Option B.**

- **Option A — keep denormalised counter, fix it.** Rewrite every status-changing site to also bump/drop the counter. Adds churn to ~5 sites; risks drift if any new status-changing code path forgets the update.
- **Option B — kill the counter, query live.** Compute `active_count = SELECT count(*) FROM listings WHERE seller_id=:s AND status='ACTIVE' AND deleted_at IS NULL` everywhere it's needed. Index on `(seller_id, status)` already exists indirectly via separate indexes; verify.

Why B: there are at most a few thousand sellers, each with ≤ 50 listings; the count query is cheap. Eliminates an entire class of drift bugs. The existing `Seller.listings_count` field becomes dead — we either drop it or rename it `total_listings_lifetime` and stop incrementing it (depends on whether any UI surfaces "lifetime").

If **Option A** chosen: introduce `Seller.active_listings_count` (new column, separate from the legacy `listings_count`), implement triggers at every status-change site, deprecate the old field with a follow-up.

### Step 2 — the canonical query

A single helper:

```python
# backend/app/services/listing_quota.py  (new)
async def get_active_listing_count(seller_id: UUID, db: AsyncSession) -> int:
    res = await db.execute(
        select(func.count(Listing.id)).where(
            Listing.seller_id == seller_id,
            Listing.status == ListingStatus.ACTIVE,
            Listing.deleted_at.is_(None),
        )
    )
    return res.scalar_one()
```

Used by: `/sellers/me/dashboard`, the new "My Listings" header, the new info banner, and the (gated) quota middleware.

### Step 3 — quota middleware (gated)

```python
# backend/app/services/listing_quota.py
async def check_can_create(seller: Seller, db: AsyncSession) -> bool:
    if settings.test_period_active:
        return True  # always allow during test period
    free = settings.free_listings_per_seller
    active = await get_active_listing_count(seller.id, db)
    if active < free:
        return True
    # In paid phase: needs an active subscription / paid slot.
    # Hook in C3: check subscription status / wallet balance.
    return False  # placeholder; real logic lives with C3
```

Use as a `Depends` on POST `/listings` and POST `/listings/claim-*`. **In test period it always returns true** — but the call site is wired and tested. When `test_period_active` flips, behaviour changes with no code change.

### Step 4 — info banner on listing-create

Frontend `frontend/src/modules/seller/pages/create-listing/ui/page/Page.tsx`:

After successful POST, if `active_count_after_create >= 3`:

```tsx
notifications.show({
  title: t("tariffs.banner.thirdListingHintTitle"),
  message: t("tariffs.banner.thirdListingHintBody"),
  color: "blue",
  autoClose: 8000,
});
```

The "active count after create" is derived from `seller.active_listing_count` returned in the listing-create response.

### Step 5 — header chip on "My Listings"

`seller/pages/listings/ui/page/Page.tsx` reads `total_active_listings` from the dashboard response (added in Step 6). Renders:

```
Активные объявления: 4 (2 бесплатных + 2 платных по завершении тестового периода)
```

i18n key: `tariffs.banner.myListingsHeader`.

### Step 6 — extend dashboard endpoint

`backend/app/api/v1/sellers.py:549-634` — add `total_active_listings` to the response. This is one extra query (or replace the existing `total_listings` with both `total_active_listings` and `total_lifetime_listings`).

### Step 7 — test-period-aware first-2 rule documentation

When `test_period_active` flips to false (Phase 2 trigger), the rule "first 2 by `created_at` are free" applies. **Today** we don't enforce this; we just need to make sure we *can* identify them deterministically. Keep `Listing.created_at` indexed (it is). No code change.

## Behaviour & invariants

- **Active count = `status=ACTIVE` AND `deleted_at IS NULL`.** Nothing else qualifies (no paused, no sold, no archived).
- **Quota middleware always returns true during test period.** It's exercised in tests; unit-testing the false branch validates Phase-2 readiness.
- **Display copy uses "тестовый период" terminology** matching C1.
- **Info banner is non-blocking** — ships exactly the same flow whether the user is at 1 or 100 active listings during test period.
- **Counter updates atomically** with status changes (Option A) OR is computed live (Option B). No middle ground.
- **Counts include claim-converted listings** — C4 multi-phone listings are counted under the same seller_id; phone-set is irrelevant for billing.
- **Lifetime listings ≠ active listings** — keep them separate or drop the lifetime concept entirely.

## Architecture notes

- The check-can-create function is the *one* gate. C3's wallet/subscription logic plugs in here when paid phase activates.
- The middleware can later evolve: in Phase 2 it returns true if active < free **OR** seller has an active subscription **OR** seller has paid for the extra slot. But that's C3's job.
- Live-count queries are single-digit-millisecond at MVP scale; no caching needed in test period.

## Upstream dependencies

- **A7** — `ListingStatus.ACTIVE` semantics — done.
- **C1** — `test_period_active` flag and config knobs. C2's middleware reads `settings.test_period_active`. **Land C1 first.**
- **A1, A4** — claim flow already exists; C2 just makes sure those paths participate in the quota check (always-true during test, real check later).

## Downstream dependencies

- **C3** — paid-phase subscription lookup hooks into `check_can_create`.
- **C4** — multi-phone is counter-neutral (all listings still count under one seller_id).
- **B5** — irrelevant (filter UI doesn't talk to quota).

## Migration / schema implications

If **Option A**: one migration adds `Seller.active_listings_count` with a backfill query.

```sql
ALTER TABLE sellers ADD COLUMN active_listings_count INTEGER NOT NULL DEFAULT 0;
UPDATE sellers s
SET active_listings_count = (
  SELECT count(*) FROM listings l
  WHERE l.seller_id = s.id AND l.status = 'ACTIVE' AND l.deleted_at IS NULL
);
```

If **Option B**: no schema change. (Recommended.)

## API implications

- `GET /sellers/me/dashboard` adds `total_active_listings`.
- POST `/listings` and POST `/listings/claim-*` gain `Depends(check_can_create_listing)` — currently a no-op, ready to gate.
- New helper service `listing_quota.py` — public surface for testing.

## Crawler / bot implications

- **Crawler:** none. The crawler creates `TelegramListing` / `OLXListing` rows, not `Listing` rows. The seller's count only goes up when they claim.
- **Bot:** no copy change today; when paid phase activates, the bot's `claim_crawled` callback may need to surface "limit reached, please subscribe" messaging. Not C2 today.

## AI / F-block implications

- **F1** (AI generation) — agnostic.
- **F3** (SEO) — agnostic.

## SEO implications

- None. Counter is private.

## Localization implications

- ~6 new keys × 3 locales (banner header, third-listing-hint title/body, dashboard "active" label, hint about counted-vs-not, "test period" reference). Keys live under `tariffs.*` matching C1.

## Infra / deploy implications

- None. No new infra.

## Edge cases

- **Backfill correctness when counter is wrong today.** If we've been mis-incrementing for months, the live-query strategy (Option B) trivially fixes it. The denormalised approach (Option A) needs a one-shot SQL backfill in the migration.
- **Race condition: two concurrent POSTs to /listings.** If a seller is on the boundary (1 free remaining) the first request must commit before the second checks. Use SELECT FOR UPDATE on the seller row, or rely on the fact that during test period the function returns true unconditionally. **Documented invariant**: the live-query path is safe at the database serialisable level for test-period; in paid phase, add `SELECT ... FOR UPDATE`.
- **Status transition timing.** If `PENDING_GENERATION` → `ACTIVE` is the moment the listing starts counting, the F1 success path *must* be the moment the seller's display jumps. Today F1 success flips the status — count is correct because it's live-queried.
- **Soft-deleted listings.** Already excluded by `deleted_at IS NULL`. Hard-deleted (cascade from user delete) drops out of count.
- **Claim of already-claimed listing.** Block A's claim endpoint short-circuits (rejects 409); the count is unchanged. Verify behaviour stays correct.
- **Restore-from-archive.** If a seller un-archives a listing, status flips back to ACTIVE — count goes up. Live-query handles this naturally.
- **Negative count guard.** `max(0, seller.listings_count - 1)` (`listings.py:3200`) is defensive; with live-query it's irrelevant.

## Operational risks

- **Counter drift survives migration day.** If we don't backfill correctly when paid phase activates, sellers may be billed for paused/sold listings or vice-versa. Live-query (Option B) eliminates this risk entirely.
- **Hidden caller of `Seller.listings_count`.** If any read path depends on the legacy field's semantics ("all non-deleted"), changing it to "active only" breaks them. Audit needed before flipping.
- **Quota middleware drift.** Once the flag flips, the false branch is the hot path. Make sure `check_can_create` has tests for both branches *now*, before anyone trusts it.

## Rollout strategy

1. Land Option B — live-query helper + dashboard field + UI banner + info-toast.
2. Wire `check_can_create_listing` as `Depends` on POST routes; behaviour unchanged.
3. Monitor in production for 2 weeks. Compare `total_active_listings` against the legacy `Seller.listings_count` to confirm the legacy was indeed broken (or quietly OK).
4. **Defer to Phase 2:** flip `test_period_active=false` and verify the false branch enforces correctly.

## Acceptance criteria

- `GET /sellers/me/dashboard` returns `total_active_listings` reflecting `status=ACTIVE` count.
- POST `/listings` accepts during test period regardless of count.
- POST `/listings` would reject during paid phase if count >= 2 — proven by unit test (does not run in production today).
- Status transition (PATCH `/listings/:id` with `status=PAUSED`) is observable on the dashboard within one request.
- "My Listings" page header shows the active count + the cost-after-test-period sentence.
- Info-toast appears on the 3rd-or-later create.
- `grep -rE "Seller\.listings_count" backend/app` shows no remaining writes if Option B is taken (or shows only the new hooks if Option A).

## Recommended PR split

- **PR1 (BE)** — `listing_quota.py` helper, `check_can_create` middleware, dashboard extension, tests.
- **PR2 (FE)** — header chip, info-toast, i18n keys.

## Estimated complexity

~1.5 dev-days BE, ~0.5 dev-day FE. Total ~2 dev-days. (Lower if Option B; ~0.5 day higher if Option A with the migration + backfill.)

## Open questions

1. **Option A vs B?** Recommendation: B. Confirm with team.
2. **Should `Seller.listings_count` legacy field be dropped or repurposed as "lifetime"?** Affects downstream UI (some places may show "lifetime listings"). Audit before deciding.
3. **What happens when paid phase activates and a seller currently has 5 active listings (3 over the limit)?** Auto-archive the latest 3? Bill them? Auto-subscribe? **Spec doesn't pin this.** Document as Phase-2 product question; safe answer is to grandfather them all in (count freezes; new ones are paid).
4. **Should claim count toward the limit (yes per spec) or be free since it's a parser-found listing?** Spec is clear: yes, count it. Confirm.

## References

- `backend/app/db/models.py:298` — `Seller.listings_count` (legacy).
- `backend/app/db/models.py:65-85` — `ListingStatus` enum.
- `backend/app/api/v1/listings.py:2849, 3016, 3200` — increment / patch / decrement sites.
- `backend/app/api/v1/claims.py:113, 232` — claim sites.
- `backend/app/services/crawler_service.py:608, 685` — convert sites.
- `backend/app/api/v1/sellers.py:549-634` — dashboard endpoint to extend.
- [C1](./C1-tariff-display.md), [C3](../hard/C3-wallet-architecture.md), [A1](../../block-a/medium/A1-claim-reject-v2.md), [A7](../../block-a/hard/A7-parser-f1-trigger.md).
