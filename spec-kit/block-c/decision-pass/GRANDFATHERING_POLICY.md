# C2 Grandfathering Policy — Decision Pass

This document closes every C2 decision raised in [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) §3 and extends [`../medium/C2-free-limit-logic.md`](../medium/C2-free-limit-logic.md) with concrete migration rules. Every choice is grounded in observed counter behaviour.

## §0 Constraints inherited from production

The truth-layer audit established:

- **`Seller.listings_count` is broken.** Six observable bugs (counter inflates on PAUSE/SOLD/EXPIRED transitions; never decrements outside hard-delete; PENDING_GENERATION counts; GENERATION_FAILED counts forever; crawler-import uses unsafe `(or 0)` pattern; `max(0, …)` masks underflow).
- **Dashboard already does live `count(*)`** (`sellers.py:569`) — but with `WHERE deleted_at IS NULL` only, NOT `status=ACTIVE`. Also wrong, just wrong differently.
- **No quota / plan / tariff logic exists** — verified absence.
- **Live count is the only trustworthy source.** `seller.listings_count` field disagrees with reality whenever any listing transitions through a non-create non-delete state.

These five facts force the seven decisions below.

---

## §1 Decision #15 — Option A vs Option B for counter strategy

🟢 **DECIDED: Option B — kill the counter, use live `count(*)`. The denormalised `Seller.listings_count` becomes dead code.**

### Comparison

| Aspect | Option A: fix counter via hooks | Option B: kill counter, live-query |
|---|---|---|
| Implementation surface | Add hooks at every status-change site (≥ 3 sites) | Replace 5 read sites with one helper |
| Backfill required | Yes — one-shot SQL to recompute every Seller's count | No |
| Drift risk over time | High — every new code path that transitions status must remember the hook | Zero |
| Concurrency safety | Requires lock or atomic UPDATE per status-change | Naturally consistent at read time |
| Cost per read | O(1) field read | O(N) per seller; N is small (≤ ~50 listings); index-supported |
| Admin / debugging | Counter says X but live-query says Y → which is true? | Single source of truth; no ambiguity |
| Decommission cost | Field stays in schema; rename to `lifetime_listings` | Drop column or stop writing to it |
| Code lines changed | ~30 (hooks at 3 sites + backfill + tests) | ~15 (helper + replace 5 reads) |

### Observed cost of `count(*)` query

```sql
SELECT count(*) FROM listings
WHERE seller_id = :s
  AND status IN ('ACTIVE', 'GENERATION_FAILED')
  AND deleted_at IS NULL;
```

Indexes that already exist:
- `seller_id` (FK index, exists by default)
- `status` (verified by audit; partial-index pattern in models.py)
- `deleted_at` (used by every public read path)

Against a seller with even 200 listings (way above MVP scale), this query returns in single-digit milliseconds. Cache for 60 seconds in Redis if profiling later shows hot-path issues.

### Implementation summary

```python
# backend/app/services/listing_quota.py (new)
async def get_billable_listing_count(seller_id: UUID, db: AsyncSession) -> int:
    """Number of listings counting toward the seller's plan limit.

    Per Block C V2.0 grandfathering policy:
    - status='ACTIVE' counts
    - status='GENERATION_FAILED' counts (visible in B2C with template)
    - All other statuses do NOT count (paused/sold/expired/pending/unconfirmed/deleted)
    """
    result = await db.execute(
        select(func.count(Listing.id)).where(
            Listing.seller_id == seller_id,
            Listing.status.in_([ListingStatus.ACTIVE, ListingStatus.GENERATION_FAILED]),
            Listing.deleted_at.is_(None),
        )
    )
    return result.scalar_one()
```

Five reads of `seller.listings_count` migrate to call this helper:
- `sellers.py:148` — public profile.
- `sellers.py:177` — `/sellers/me`.
- `sellers.py:218` — `PATCH /sellers/me`.
- `sellers.py:458` — public profile (duplicate route).
- `sellers.py:569` — dashboard (already live-queries; just narrows to `status IN`).

### What stays in code (deprecated)

- `Seller.listings_count` column stays in DB. Drop is a separate Phase-2 cleanup migration.
- Increment hooks at 5 sites (listings.py:2849, claims.py:113, 232, crawler_service.py:608, 685) **stay** to avoid breaking any downstream consumers we haven't found. The field becomes write-only-but-unused.
- Decrement hook at listings.py:3200 stays. Same reason.
- Future cleanup PR: rename column to `lifetime_listings_count` (semantic alignment) or drop entirely after audit confirms zero readers remain.

### Why Option B wins

- **Zero migration risk.** No backfill SQL, no drift window, no production data alteration.
- **Self-correcting.** Whatever the counter happens to be drifting toward, it's irrelevant — reads ignore it.
- **Removes the bug class entirely.** Instead of "fix this hook, then this hook, then this other hook", we say "the field is no longer authoritative".
- **Matches dashboard's existing pattern** at `sellers.py:569`.

---

## §2 Per-seller scenarios (status × billability matrix)

For reference. Drives the live-query helper.

| Status | Counts toward limit? | Visible in B2C? | Why |
|---|---|---|---|
| `ACTIVE` | YES | YES | live, public listing |
| `PAUSED` | NO | NO | seller has hidden it; not "live" |
| `SOLD` | NO | NO | transaction concluded; not "live" |
| `EXPIRED` | NO | NO | system-aged out; not "live" |
| `DELETED` | NO | NO | soft-deleted; not "live" |
| `PENDING_GENERATION` | **NO** (decision #17) | NO | F1 still running; user hasn't seen the listing |
| `GENERATION_FAILED` | YES (decision #18) | YES (with template description) | listing is live to buyers |
| `UNCONFIRMED` | NO | NO | parser couldn't extract enough; admin queue only |

### Helper expression

```
billable = status IN ('ACTIVE', 'GENERATION_FAILED') AND deleted_at IS NULL
```

That's the entire predicate. Applied uniformly: `get_billable_listing_count()`, `check_can_create_listing()`, displayed counters in UI.

---

## §3 Decision #16 — Grandfathering policy on flip day

🟢 **DECIDED: Option A — grandfather all currently-billable listings.**

### Three options compared

#### Option A — Grandfather

When `test_period_active=false` flips:
- Sellers' currently ACTIVE/GENERATION_FAILED listings remain billable but **continue without payment**. The seller is over-the-limit but not in violation.
- New creates (and claims) above the free limit require active subscription / paid slot.
- Cumulative drop-off: only as paused listings cycle back to ACTIVE. Existing inventory is preserved.

#### Option B — Hard-block

When the flag flips:
- Sellers above the free limit **cannot create new listings**, full stop, until they pay or archive existing ones.
- Existing listings stay live (we don't auto-archive — that would be punitive).
- Pause/un-pause behaves normally; un-pausing a listing while over the limit raises 402.

#### Option C — 30-day soft warning

When the flag flips:
- For 30 days, behaviour is identical to Option A (grandfather).
- After day 30, behaviour switches to Option B (hard-block on new creates).
- During the 30 days, the dashboard shows a counter "вы используете N бесплатных мест из 2 — со 2 июня — оплата".

#### Comparison matrix

| Criterion | A: grandfather | B: hard-block | C: 30-day grace |
|---|---|---|---|
| Migration complexity | Trivial (no behaviour change for existing) | Trivial (just enable middleware) | Medium (date arithmetic) |
| UX fallout day 1 | Zero — invisible to users with N≤2 | High for users with N>2 | Low — banner, no blocker |
| Abuse vectors | Sellers may keep over-the-limit indefinitely; cost = unbilled service | Sellers might delete existing to free slots — same as A in 30 days | Same as A; just delayed |
| Operational burden | Low — no ops events expected | High — support tickets from "why can't I publish" | Medium — banners, FAQ updates |
| Support burden | Low | High first week | Medium — stretched over 30 days |
| Implementation | `check_can_create_listing` reads `test_period_active` | Same | Same + `flip_date` setting + date math |
| Rollback complexity | Trivial — flip back to test_period_active=true | Trivial | Trivial |
| Fairness perception | High — "you got in early; thanks" | Low — "rules changed without warning" | Medium — "we gave you 30 days" |
| Seller scenarios at flip day | All preserved | N>2 sellers blocked | All preserved for 30 days, then N>2 blocked |

### Recommendation: Option A

Reasoning anchored in spec V2.0:

> "Тестовый период earns trust"

Punishing existing sellers on flip day breaks that contract. The free 2-listing tier is permanent (per spec) — the *additional* listings these sellers have were created in good-faith during the test period.

Option A's downside (seller keeps over-the-limit indefinitely without paying) is bounded by:
- Pause/un-pause cycle eventually moves listings out of the count.
- The seller's incentive to claim more listings (post-Found) is the natural pressure to subscribe.

Option C is technically valid but adds date-math complexity for a marginal UX benefit. Recommend **A** with no grace period.

### Edge case: flip day timing

On flip day:
1. `test_period_active=false` set in config.
2. `check_can_create_listing()` starts returning false for sellers with `current_billable_count >= 2`.
3. Seller dashboard banner switches from "тестовый период" to "тариф активен".
4. **No retro-active billing.** No alert banner about being over-the-limit. Nothing to do.
5. Seller's first attempt at NEW create → 402 with message "первые 2 бесплатно; пополните кошелёк или оформите подписку Кабинет".

---

## §4 Decision #17 + #18 — `PENDING_GENERATION` and `GENERATION_FAILED` counts

🟢 **DECIDED: Only `ACTIVE` and `GENERATION_FAILED` count toward the limit. `PENDING_GENERATION` does NOT count.**

### Rationale for `PENDING_GENERATION` excluded

- A claimed listing in `PENDING_GENERATION` is **invisible to buyers** until F1 completes. Per Block A's buyer feed query (`listings.py:1182`), the feed gates on `status IN (ACTIVE, GENERATION_FAILED)`.
- The seller hasn't yet "received the value" of having a listing live in the marketplace.
- F1 latency is system-side. Charging the seller for that latency is unfair.

### Rationale for `GENERATION_FAILED` included

- Per Block A's spec, GENERATION_FAILED listings are shown in B2C with a **template description** synthesised from structured params.
- The buyer feed includes them (verified at `listings.py:1182`).
- The listing is "live" — it provides marketplace value to the seller.
- Treating it as billable is consistent with treating ACTIVE as billable.

### What this means in practice

- Seller claims an OLX listing → status flips to `PENDING_GENERATION`. Counter does NOT bump.
- F1 succeeds → status flips to `ACTIVE`. Counter bumps **at this moment**.
- F1 fails permanently → status flips to `GENERATION_FAILED`. Counter bumps **at this moment**.
- Edge case: F1 takes hours, seller doesn't see counter increase for hours. Acceptable; the listing isn't earning marketplace value yet.

### Live-query implication

Single predicate covers both cases:

```python
status.in_([ListingStatus.ACTIVE, ListingStatus.GENERATION_FAILED]) AND deleted_at IS NULL
```

No special-casing needed.

---

## §5 Decision #19 — First-2-free rule

🟢 **DECIDED: Live "oldest 2 currently-billable by `created_at`" are free.**

### Rationale

Three alternative semantics considered:

- **(α) Pin first-2 at flip-day:** record the IDs at flip day; those two are free forever, others always cost. Pro: predictable; con: seller can't change which 2 are free; high admin burden ("but I want to swap").
- **(β) Live oldest-2 by `created_at`:** at any moment, the seller's two oldest billable listings are the free slots. Pro: predictable + flexible — seller can archive the oldest (e.g., a sold listing) to "free up" a slot for a newer one. Con: requires live evaluation.
- **(γ) Seller chooses 2 manually:** UI for seller to pick. Pro: ultimate control; con: more UX, more admin support for "I forgot to pick".

Recommend **(β)**. It's the live-query model's natural fit; no extra schema; clear UX message ("первые 2 бесплатно — самые старые из активных").

### Implementation

`check_can_create_listing` doesn't need to know which 2 are free — it just compares billable count against the free limit. The "which are free" question is purely a UI display concern.

UI concern: when the seller views their listings, the two oldest billable ones are tagged "Бесплатно" (or similar label); the rest show "Платное". This requires sorting their listings by `created_at` ASC and tagging the first two.

---

## §6 Decision #20 — Status transition counter rules (paid phase)

🟢 **DECIDED: All transitions are computed live; no manual counter delta.**

### Live-query implication

When the flag flips and live-query is the source of truth, status transitions don't "update the counter" — the counter recomputes automatically on every read. Therefore:

| Transition | Counter delta (effective) | Notes |
|---|---|---|
| nothing → ACTIVE (create / claim final state) | +1 | listing now billable |
| ACTIVE → PAUSED | -1 | not billable |
| PAUSED → ACTIVE | +1 | re-enabled, billable |
| ACTIVE → SOLD | -1 | sale closed; slot freed |
| SOLD → ACTIVE | +1 | re-listed |
| ACTIVE → DELETED (soft) | -1 | freed |
| ACTIVE → EXPIRED | -1 | aged out |
| PENDING_GENERATION → ACTIVE | +1 | now billable |
| PENDING_GENERATION → GENERATION_FAILED | +1 | now billable |
| GENERATION_FAILED → ACTIVE | 0 | both billable |
| ACTIVE → UNCONFIRMED (admin) | -1 | admin override; freed |
| UNCONFIRMED → ACTIVE (admin) | +1 | reclaimed |

The counter doesn't care about transitions per se — it just queries on every check. Transitions happen via the existing `PATCH /listings/{id}` endpoint, which doesn't need new code paths.

### Quota gate timing

`check_can_create_listing` is called at:
- `POST /listings` — before creating.
- `POST /listings/claim-olx/{id}`, `POST /listings/claim-telegram/{id}` — before claiming.
- `PATCH /listings/{id}` when transitioning to ACTIVE from a non-billable state (re-publishing) — **NEW**: this is where un-pause must check.

The third site is the **non-obvious** one. A seller with 5 paused listings and 2 active (= 2 billable) tries to un-pause one → that's a transition to a 3rd billable. Quota gate must catch it.

**Implementation:** the PATCH endpoint at `listings.py:3016` checks before applying the status flip; if the new status is ACTIVE and the count would exceed limit, reject with 402.

---

## §7 Decision #29 — Soft user-side "merge accounts?" prompt (deferred)

🟡 **RECOMMENDED: Defer to post-launch.**

### Rationale

This is the C5 cross-reference. The phase brief asked it under C2; the answer is shared with C5.

- C5's signal-detection runs in admin queue; admin acts.
- The user-side prompt ("we noticed you have another account, want to merge?") risks accusatory tone for false positives.
- Recommend: ship signal detection + admin queue first; observe false-positive rate for 4+ weeks; only then add user-side prompt if rate is acceptable.

---

## §8 Test-phase → production-phase flip procedure

The flag flip is the most operationally sensitive moment. Procedure:

1. **T-7 days:** founder announces in-app banner + Telegram bot DM: "тестовый период завершается через 7 дней. ваши N объявлений останутся активными, новые сверх лимита будут платными".
2. **T-1 day:** final reminder.
3. **T-day morning (low-traffic window):**
   - Admin sets `test_period_active=false` via the existing config knob.
   - Caches invalidated (Redis `tariffs:status:v1` and similar).
   - The new banner copy goes live on `/seller/tariffs` and `/seller/listings` headers.
4. **T-day +1 hour:**
   - Verify dashboards display correctly.
   - Spot-check 5 sellers' counts via admin tool — match live query.
   - Monitor 402 error rate (sellers hitting the new limit). Should be very low; first attempts mostly come from sellers already at 1-2 listings.
5. **T-day +24 hours:**
   - Review C5 admin queue for any anomalous signals.
   - Verify no production errors related to wallet operations (since wallet is still test-period-stub).
6. **T-day +7 days:**
   - Compare seller-side complaints / support tickets against expected pattern.
   - Measure subscription rate.

### Rollback procedure

Single-step: `test_period_active=true` again. The system reverts to display-only mode immediately. No data loss; no schema changes.

---

## §9 Edge cases

### Seller with 0 active listings

- Counter = 0, free limit = 2.
- Can create 2 free listings; 3rd requires payment in paid phase.
- Test phase: can create unlimited; informational toast on 3rd-and-later create.

### Seller with exactly 2 active listings

- Counter = 2 = free limit.
- Cannot create a 3rd without subscription.
- Pause one → can create another free one.

### Seller with 20 active listings (existing, pre-flip)

- Per Option A grandfathering: all 20 stay live.
- Cannot create a 21st without subscription.
- 18 of those 20 are "above the free 2"; if the seller subscribes to listing-extra, those 18 cycle into paid status. If not, no billing happens but no NEW creates allowed.

### Paused / archived listings

- Don't count toward limit.
- Un-pausing one transitions to ACTIVE; quota check fires at the PATCH endpoint.
- Archived listings can be restored; same gate.

### Pending_generation listings

- Don't count.
- F1 may take seconds to minutes. Counter "ticks up" when F1 finishes.

### Failed AI generation listings

- Count.
- Listing is live in B2C with template description.

### Deleted listings

- Don't count.
- Soft-deleted; could be undeleted via admin, at which point quota check fires.

### Hard-deleted users

- All their listings cascade to either soft-deleted or NULL'd `seller_id` (per existing FK behaviour).
- Quota check on a deleted user's wallet is moot (no future creates).

### Buyer-to-seller upgrades

- New Seller created with `listings_count = 0` (legacy field default).
- Live count returns 0 — same.
- Free 2 slots available immediately.

### Multi-phone (C4) interaction

- All listings claimed via any of the seller's verified phones count under the SAME seller_id.
- A seller with 3 phones and 8 listings has 8 billable listings (assuming all ACTIVE), not 3 × 2 free = 6 free + 2 paid.

### Concurrent create on the boundary

- Seller has 1 ACTIVE (1 billable). Two concurrent POST `/listings` requests arrive.
- Both call `check_can_create_listing`. Both see count=1, both pass.
- Both INSERT a Listing → seller now has 3 billable.
- **Acceptable in test phase** (no enforcement).
- **In paid phase:** add a serialisable transaction or `SELECT FOR UPDATE` on the seller row before the count query. Cost: ~10 lines, but only relevant when paid-phase enforcement is live.

This is a known race; document and revisit when the flag flips.

---

## §10 Implementation gates (C2-related)

| Gate | Owner | Done before |
|---|---|---|
| `listing_quota.py` helper with `get_billable_listing_count` and `check_can_create_listing` | Backend dev | Test-period UI ships |
| Feature-flag-gated `Depends(check_can_create_listing)` on POST routes | Backend dev | C2 PR1 |
| Migrate 5 read sites of `seller.listings_count` → live helper | Backend dev | C2 PR1 |
| Dashboard `/sellers/me/dashboard` returns `total_billable_listings` | Backend dev | C2 PR1 |
| FE: "X active (Y free, Z paid after test period)" header | Frontend dev | C2 PR2 |
| FE: 3rd-create info-toast | Frontend dev | C2 PR2 |
| Feature flag `test_period_active` in `config.py` | Backend dev | Same release as C1 |
| Native-speaker review of test-period copy | Operations | Pre-launch |
| Document flip-day procedure in ops runbook | Operations | Pre-launch |

---

## §11 Cross-spec links

- [`DECISION_MATRIX.md`](DECISION_MATRIX.md) — master matrix.
- [`../medium/C2-free-limit-logic.md`](../medium/C2-free-limit-logic.md) — full C2 spec.
- [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) §3 — counter audit.
- [`../medium/C1-tariff-display.md`](../medium/C1-tariff-display.md) — UI consumer of `test_period_active`.
- [`../hard/C5-multi-account-detection.md`](../hard/C5-multi-account-detection.md) — anti-abuse layer.
