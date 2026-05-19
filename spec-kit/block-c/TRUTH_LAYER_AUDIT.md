# Block C — Truth-Layer Audit (Pre-Spec)

This document is the **system truth** before any architecture work for Block C. Every claim is grounded in real code with file:line references. Where the codebase is silent, the gap is documented as an OPEN QUESTION rather than filled with assumption.

Sections:
1. **OTP System Audit Report** (Phase 1)
2. **C3 Wallet Requirement Spec** (Phase 2 — derived from production constraints, not invented)
3. **C2 Grandfathering Requirement Spec** (Phase 3 — derived from observed counter behaviour)
4. **Open Questions** (explicit; no silent product assumptions)
5. **Risk Matrix** (production, migration, race conditions)

---

# 1. OTP SYSTEM AUDIT REPORT

## 1.1 Production truth path — single canonical flow

The **only** OTP path that runs end-to-end in production is the **Seller Phone-OTP login**:

1. **Endpoint:** `POST /auth/seller-otp` → `request_seller_otp` at `backend/app/api/v1/auth.py:766-906`.
2. **Code generation:** `core/security.py:149` — `generate_otp()` returns a 6-digit numeric string.
3. **Delivery channel:** **Telegram bot DM**. `auth.py:879` calls `bot.send_message(chat_id=tg_id, text=f"🔐 Код для входа …\n<code>{otp_code}</code>", parse_mode="HTML")`. **No SMS.**
4. **Storage:** Redis, three keys per phone-suffix:
   - `seller_otp:{last9}` — code, TTL 600s.
   - `seller_otp_attempts:{last9}` — failed-attempt counter, TTL 600s.
   - `seller_otp_tg:{last9}` — telegram_id pinned for new-user creation on verify, TTL 600s.
   - Plus rate-limit: `rate_limit:seller_otp:{last9}` — 3 requests / 10 min.
5. **Verification:** `POST /auth/verify-seller-otp` at `auth.py:909-1038`. Up to 3 attempts; on success, deletes Redis keys; either looks up an existing User by phone or **creates a new User + Seller** (auth.py:957-1029) with `auth_source="seller_otp"`; issues JWT access + refresh, sets httpOnly cookies.

## 1.2 Telegram-WebApp auth ≠ OTP

Confirmed: **Telegram-WebApp users do NOT hit OTP.** Recent commits `d25105e — feat(auth): phone-gated Telegram WebApp auth for sellers` and `3a565e0 — fix(auth): defend Mini App against Telegram account switching` enforce phone-gating but use the WebApp's `initData` signature for primary identification, not OTP. The OTP endpoint exists for direct-phone-login (the rare path where the user starts from a saved Telegram link or brand-new device).

## 1.3 Additional OTP flow — Listing claim — BROKEN

`backend/app/api/v1/claims.py:35-244` defines a separate OTP flow for "I claim that this parser-listing is mine when my phone DOESN'T match the listed phone".

**Production behaviour:** The fast path is auto-verify when `seller.phone == listing.phone` (no OTP). The OTP fallback path is broken:

```python
# claims.py:150
await redis.setex(CacheKeys.otp(listing.phone), 600, otp_code)

# backend/app/db/redis.py:39-83 — CacheKeys class
@staticmethod
def seller_otp(phone: str) -> str:
    return f"seller_otp:{phone}"
# … no `otp()` staticmethod exists.
```

**Verified by `grep`**: `CacheKeys.otp` is called at `claims.py:150, 208, 235` but the staticmethod is **not defined** in `redis.py`. Any execution raises `AttributeError`.

**Why this hasn't broken in production:** the auto-verify (phone_match) short-circuit handles the common case. The OTP fallback is rare in real traffic (sellers register with the same phone they use in their listings).

## 1.4 SMS / Eskiz status

**ABSENT.** Verified by:

- No `eskiz`, `sms`, `Twilio`, `notify.eskiz.uz` imports anywhere in `backend/`.
- No `SMS_*`, `ESKIZ_*` env vars in `backend/app/core/config.py:11-188`.
- Nothing in `requirements.txt`.
- Single mention is `# TODO: Send OTP via SMS` at `claims.py:157` — a comment, not code.

**Conclusion:** The phrase "OTP via SMS" in any user-visible copy or spec is currently a **lie** with respect to the code. Any product material referring to "we'll text you" needs to either be rewritten to "we'll Telegram you" or wait until SMS is actually integrated.

## 1.5 Frontend OTP UI

The seller-register page (`frontend/src/modules/seller/pages/register/`) and `become-seller` page do not present an OTP-input UI directly — they assume Telegram-WebApp authentication. The OTP-input UI used by direct phone-login lives elsewhere (route to confirm). The frontend has no SMS-vs-Telegram channel selector — confirmation: there is no toggle because there is only one channel.

## 1.6 Race condition in verify → user-creation path

`auth.py:967-1006` is **not wrapped in a transaction lock**. Two concurrent `POST /auth/verify-seller-otp` requests for the same phone could both pass the "user exists?" check (both see no row) and both attempt INSERT, hitting a UNIQUE-violation on the second. This is a small but real concurrency seam — relevant when sellers click "verify" twice while waiting for slow network. Recoverable (one request fails, user retries) but messy.

## 1.7 Phone-suffix collision risk

OTP Redis keys use the **last 9 digits** of the phone. UZ is `+998` so this is currently safe. Adding any other country would break dedup — the canonicalised E.164 path established by `prf_canonicalize_phone` migration (Block A) makes this a forward-compat trap.

## 1.8 Gaps for C4 (multi-phone OTP)

| Item | Today | Required for C4 |
|---|---|---|
| OTP Redis keys | `seller_otp:{last9}` (login-scoped) | New namespace e.g. `add_phone_otp:{user_id}:{last9}` to avoid cross-talk |
| User-creation side effect | Verify creates a User if none exists | Add-phone path must NEVER create a user; must reject if phone already attached elsewhere |
| Delivery channel | Telegram bot | Same channel — but verify the user is reachable on Telegram (already authenticated) |
| Endpoint | `/auth/verify-seller-otp` (login flow) | New `/sellers/me/phones/verify-otp` (auth-required, additive) |
| Storage | `Seller.phone` is single | New `user_phones` table per the Block C spec-kit |

## 1.9 Conflicts and duplications

- **Login OTP and claim OTP use different Redis-key patterns** (`seller_otp:` vs `otp:` — though the latter is broken). No active collision.
- **`verification_otp` field on `ListingClaim` model duplicates the Redis OTP storage.** Two sources of truth for the same code. Today they're both written; only the DB version is read by the verify endpoint when the Redis lookup fails. **Documented technical debt.**

## 1.10 What this means for Block C

- **C4 cannot ship "SMS verification" today.** Default to Telegram-bot OTP and document the channel choice in user-facing copy.
- **The claim-OTP `CacheKeys.otp` bug must be fixed independently** — it's a live latent bug, not a Block C deliverable, but Block C touches the same surface.
- **C4's add-phone OTP must use a separate Redis-key namespace** to avoid cross-talk with login flow.
- **C4's verify endpoint must be NON-creating** — it attaches an additional phone to the *current authenticated user*, never creates a new user.
- **The verify→create race condition in login** (1.6) is unrelated to C4 but should be fixed in the same audit pass.

---

# 2. C3 WALLET REQUIREMENT SPEC

## 2.1 Current state — confirmed absences

- **Models:** No `Wallet`, `Transaction`, `Subscription`, `Plan`, `Payment`, `Invoice`, `Billing`, `Charge`, `Refund`, `Promotion`, `Coupon` classes anywhere in `backend/app/db/models.py`.
- **Migrations:** Zero alembic files reference billing tables.
- **Endpoints:** No `wallet.py`, `payments.py`, `subscriptions.py`, `billing.py` modules.
- **Settings:** No `CLICK_*`, `PAYME_*`, `MERCHANT_*` env vars. Only `exchange_rate_api_url` (config.py:177) and `exchange_rate_fallback: int = 12_800` (config.py:178).
- **Bot:** No payment commands, no Telegram-Payments-API usage.

## 2.2 Adjacent state we DO observe

- **`Listing.is_boosted: bool` and `Listing.boost_until: Optional[datetime]`** (models.py:552-553) — declared, defaulted false / null. Verified by grep: **never set anywhere** outside the column declaration. Read-only by ranking logic in `buyer.py` and `search_index.py:127`. **Skeleton field; not yet plumbed to anything.**
- **`Listing.rent_payment` array** — string-list of accepted-payment-methods metadata (cash/payme/click/bank). Display-only; not enforced.
- **Currency enum** (models.py:103-108): `UZS`, `USD`. Used by `Listing.currency`.
- **Exchange-rate plumbing:** `exchange_rate_api_url` setting + a daily Celery task at `workers/tasks/listings.update_exchange_rates`. Result cached in Redis at `rate:usd_uzs`.

## 2.3 Production constraints that bound the future wallet

These observations come from existing critical paths and are non-negotiable for a wallet that ships into the same codebase.

### 2.3.1 Concurrency primitives in use

- **`SELECT FOR UPDATE` row-level locks** are used in the claim flow at `backend/app/api/v1/listings.py` (~lines 2200, 2400) on `OLXListing` / `TelegramListing` rows during claim/reject. Pattern: `select(Model).where(Model.id == ...).with_for_update()`. Lock scope is **single row, exclusive**. Comment in `services/crawler_service.py` says: "caller must hold a SELECT FOR UPDATE lock on `olx` and handle commit/rollback." **This is the precedent for any wallet-balance lock.**

### 2.3.2 Idempotency primitives in use

- **`ON CONFLICT … DO UPDATE` additive merge** at `admin_sources.py:626-657` (Block A's source-metric writeback). Pattern: `INSERT … ON CONFLICT (key) DO UPDATE SET col = source.col + EXCLUDED.col`.
- **Unique partial index** for crawled-match notification dedup at `models.py:1182-1188` (`Notification` `uq_notification_crawled_match` with `WHERE type = 'crawled_match'`).
- **Unique partial index** for one-OLX-listing-to-one-Listing at `models.py:1570-1576` (`uq_olx_converted_listing` with `WHERE converted_listing_id IS NOT NULL`).

### 2.3.3 Money-precision discipline TODAY

**`Listing.price` is `Integer`** (models.py:470), not `Decimal`. UZS prices are whole-currency-unit; USD is also stored as whole-dollar (no cents). **No `Decimal` type used anywhere in `backend/app/`.**

`TelegramListing.price` and `OLXListing.price` are `Float` (parser uncertainty); coerced to `int` on import via `int(data.price)` in `crawler_service.py:611, 686`.

**Implication:** the wallet must use either `Integer` (matching the existing convention, sub-unit precision via "store amount in tiyin/cents") OR break the convention with `Numeric`. **The codebase precedent is integer; the spec needs to choose explicitly.**

### 2.3.4 Audit-log usage pattern

`AuditLog` (models.py:1316-1345) has columns: `id`, `user_id`, `entity_type`, `entity_id`, `action`, `old_values` JSONB, `new_values` JSONB, `ip_address`, `user_agent`, `created_at`. It IS written from admin moderation endpoints in `admin.py` (lines 244-257, 273-289, 310-319, 335-351). **Pattern is repeatable but NOT yet standardised** — some endpoints flush before audit, others after.

### 2.3.5 Adapter pattern precedent

There is **no Protocol/ABC pattern** in the backend. The closest analog is the **search-backend toggle**: `config.py:85` `search_backend = "postgres"|"meili"` selects the backend via `if/elif` in `buyer.py` and `search_router.py`. **The codebase prefers configuration-driven if/elif over abstract interfaces.** Click/Payme adapters should follow this convention rather than introducing a Protocol.

## 2.4 Wallet lifecycle states & invariants (REQUIREMENTS)

Derived from the production constraints above. **These are the rules a future implementation must satisfy. They are not a design or schema.**

### 2.4.1 When does a Wallet row exist?

**Two valid options:**

- **Eager:** Wallet is created in the same transaction as the User (e.g., extending `auth.py:957-1006`'s "create-user-on-first-OTP-verify" path). Pros: every User has a Wallet, every code path can assume one exists. Cons: backfill required for existing Users at migration time.
- **Lazy:** Wallet is created the first time it is needed (first deposit, first balance read, or first attempted withdraw). Pros: zero backfill. Cons: every withdraw / deposit must do `INSERT … ON CONFLICT DO NOTHING` to handle the race.

**Constraint from production:** Whichever option is chosen, the create operation MUST be idempotent under concurrent calls. The auth.py:957-1006 race condition is the precedent here — any wallet-creation path that is not lock-protected or `ON CONFLICT`-protected will exhibit the same race.

**Recommendation (not yet a decision):** lazy creation, gated by `INSERT … ON CONFLICT (user_id) DO NOTHING` plus immediate `SELECT … FOR UPDATE` on the wallet row. This avoids the auth-time backfill and matches the codebase's idempotency-at-the-write-path style.

### 2.4.2 Valid balance transitions

- **Balance is non-negative.** A withdraw that would make `current_balance < 0` MUST fail before any mutation. Constraint: `CHECK (current_balance >= 0)` at the DB level OR enforced before commit at the service layer.
- **Balance only changes via Transaction commit.** No "free" balance updates — every mutation is paired with a Transaction row (deposit, withdrawal, refund, adjustment).
- **Concurrency safety:** every balance mutation MUST hold a `SELECT … FOR UPDATE` on the Wallet row before computing the new value. This is the production precedent (claim flow uses it on the source-listing row).

### 2.4.3 Valid Transaction status transitions

- `pending → completed` (provider confirmed payment).
- `pending → failed` (provider rejected; balance unchanged).
- `completed → refunded` (refund-of chain via metadata).
- **Forbidden:** `failed → completed`, `completed → pending`, `refunded → completed`. State machine is **monotonic** except for the `completed → refunded` step.

### 2.4.4 Required idempotency

- **Every Transaction MUST carry an `idempotency_key`** unique per logical operation. Webhook re-delivery from Click/Payme MUST hit the unique constraint and be a no-op, not a double-credit.
- **Pattern from production:** Block A's `Notification.uq_notification_crawled_match` and `OLXListing.uq_olx_converted_listing` partial unique indexes. Apply the same idea: `UNIQUE (idempotency_key)` (full unique) or `UNIQUE (external_payment_id) WHERE external_payment_id IS NOT NULL` (partial unique).

### 2.4.5 Required audit-logging

- Every `Transaction` status transition writes an `AuditLog` row (`entity_type="transaction"`, `entity_id=tx.id`, `action="status_change"`, `old_values`/`new_values` capture status + balance delta).
- Every admin balance adjustment writes an `AuditLog` row including `actor_id` (admin) and the mandatory reason in `new_values.reason`.
- `Wallet` row creation does **not** require audit (creation is a derived event, not a state change).

### 2.4.6 Currency invariant

- One Wallet has one currency. **Mixed-currency operations on a single wallet are forbidden.**
- `Wallet.currency` and `Transaction.currency` MUST match for any transaction touching that wallet.
- USD and UZS exist as enum values today; **MVP can ship UZS-only** and reject USD operations at the service layer with a clear error. Multi-currency is a Phase-2 / Phase-3 expansion.

### 2.4.7 Forbidden states / impossible combinations

- `Transaction.amount <= 0` is invalid (rejected at schema validation; not just service layer).
- `Transaction.status='completed'` AND `Transaction.completed_at IS NULL` is invalid (must be set in the same write).
- `Subscription.type='listing_extra'` AND `Subscription.object_id IS NULL` is invalid (must point to a listing).
- `Subscription.status='active'` AND `next_billing_at IS NULL` is invalid (active subs always know when they bill next).
- `Wallet.current_balance < 0` is invalid in steady state. Transient negative during a withdraw transaction is allowed only inside the SELECT FOR UPDATE window and must be rejected before commit.

### 2.4.8 Money-unit invariant

- All money values are stored in the **smallest currency unit** consistent with the existing `Listing.price` integer convention.
- For UZS, the smallest unit is **1 UZS** (no fractional sub-unit in everyday use). Storing `current_balance` as `BIGINT` (UZS) is sufficient and matches `Listing.price`'s `Integer` storage.
- Recommendation (not decision): use `BIGINT` for all monetary columns; document the convention in the migration.

### 2.4.9 Transaction immutability

- `Transaction` rows are append-mostly. The **only fields that mutate after creation** are:
  - `status` (one-way: pending → completed/failed; completed → refunded)
  - `completed_at` (set once, when status flips to completed)
  - `metadata` (JSONB) for context that wasn't known at creation
- All other fields (`amount`, `currency`, `wallet_id`, `idempotency_key`, `external_payment_id`, `subscription_id`) are **immutable** after the row is committed.

## 2.5 Open architecture questions (Phase 2 spec needs to answer)

See section 4.

---

# 3. C2 GRANDFATHERING REQUIREMENT SPEC

## 3.1 Current state — confirmed bugs

`Seller.listings_count` (models.py:298) is a denormalised `Integer` counter. Its production behaviour is **wrong** in three observable ways:

### 3.1.1 Counter inflates on PAUSE/SOLD/EXPIRED transitions

- The increment sites (`listings.py:2849`, `claims.py:113, 232`, `crawler_service.py:608, 685`) all bump unconditionally on create or claim.
- The PATCH `/listings/{id}` endpoint at `listings.py:3016-3017` mutates `listing.status` but **never touches `seller.listings_count`**.
- **Reproduction:** a seller creates 3 listings (counter=3), pauses 2 (counter still 3, but live `count(*) WHERE status=ACTIVE` is 1).
- **Source of truth divergence:** public seller profile (`sellers.py:148, 177, 218, 458`) returns the stale `seller.listings_count`. Dashboard (`sellers.py:569`) uses live `count(*) WHERE deleted_at IS NULL` — also wrong (includes paused/sold).

### 3.1.2 Counter inflates on PENDING_GENERATION

- Block A V2.0's claim flow flips status to `PENDING_GENERATION` at `listings.py:2325, 2517` **after** the increment (lines 2849, etc.).
- **Reproduction:** a seller claims a Telegram listing → `seller.listings_count += 1`, `listing.status = PENDING_GENERATION`. The listing is invisible in B2C until F1 succeeds, but counts as billable.
- If F1 fails permanently → `status='generation_failed'` — still counted forever.

### 3.1.3 Counter never decrements on status transitions

The only decrement site is the soft-delete endpoint at `listings.py:3200`: `seller.listings_count = max(0, seller.listings_count - 1)`. **`max(0, ...)` masks underflow** but doesn't fix the root cause — pause/sold/expired transitions don't decrement.

## 3.2 Live truth: dashboard query

The **dashboard live query** at `sellers.py:569` is closer to truth than the denormalised counter:

```python
func.count(Listing.id).label("total_listings")
.where(
    Listing.seller_id == seller.id,
    Listing.deleted_at.is_(None),
)
```

Still wrong: includes PAUSED/SOLD/EXPIRED. To match the spec's "active = `status=ACTIVE`" rule, the WHERE must add `Listing.status == ListingStatus.ACTIVE`.

## 3.3 Status × billability matrix (per Block-A V2.0 spec interpretation)

| Status | Visible in B2C? | Counts toward billing limit? | Counter reflects this? |
|---|---|---|---|
| `ACTIVE` | YES | YES | counter ++ on create |
| `PAUSED` | NO | NO (seller-controlled hide) | counter NEVER drops — **bug** |
| `SOLD` | NO | NO | counter NEVER drops — **bug** |
| `EXPIRED` | NO | NO | counter NEVER drops — **bug** |
| `DELETED` | NO | NO (soft-deleted) | counter -- on delete |
| `PENDING_GENERATION` | NO | **debatable** — see 3.5 | counter ++ on claim — **bug or feature?** |
| `GENERATION_FAILED` | YES (with template) | YES | counter ++ on claim, never drops |
| `UNCONFIRMED` | NO (admin only) | NO | not seen via increment paths today |

## 3.4 No quota / plan / tariff logic exists today

Verified by grep:
- No `MAX_LISTINGS_PER_SELLER` constant.
- No `Seller.plan`, `Seller.tier`, `User.plan` field.
- No quota middleware (`Depends(check_quota)` etc.).
- No 402 / 409 responses for over-limit creates.
- A seller can create 100 listings today with no system pushback.

## 3.5 Derived requirements for grandfathering

These rules are derivable from the production-behaviour audit. They are NOT product decisions — product still needs to confirm the contested edge cases (3.5.5).

### 3.5.1 Source of truth on flip day

When `test_period_active=false` is set, the source of truth for "how many active listings does seller X have" is the **live query**:

```sql
SELECT count(*) FROM listings
WHERE seller_id = :s AND status = 'ACTIVE' AND deleted_at IS NULL
```

The denormalised `Seller.listings_count` is **not trustworthy** and MUST NOT be the basis for any billing decision.

**Implication:** the recommended path for C2 is to abandon `Seller.listings_count` for billing purposes (treat it as "lifetime listings" or drop it) and compute the active count live. This avoids a costly migration / backfill on flip day.

### 3.5.2 Status transitions in the paid phase

Once the flag flips:

| Transition | Counter delta | Why |
|---|---|---|
| nothing → ACTIVE (create / claim) | +1 (live) | new active listing |
| ACTIVE → PAUSED | -1 (live) | seller frees a slot |
| PAUSED → ACTIVE (un-pause) | +1 (live) | seller reclaims a slot |
| ACTIVE → SOLD | -1 (live) | sale closes; slot freed |
| SOLD → ACTIVE | +1 (live) | re-listing the same property |
| ACTIVE → DELETED | -1 (live) | soft-delete; slot freed |
| ACTIVE → EXPIRED | -1 (live) | system-triggered expiry; slot freed |
| PENDING_GENERATION → ACTIVE | +1 (live) | F1 finished; listing visible — **see 3.5.5 (PG question)** |
| PENDING_GENERATION → GENERATION_FAILED | +1 (live, since GF counts) | template description shown in B2C |
| ACTIVE → UNCONFIRMED | -1 (admin override only) |  |
| UNCONFIRMED → ACTIVE | +1 |  |

### 3.5.3 Existing-seller migration on flip day

Three legitimate options:

- **(A) Grandfather.** Sellers who already have N > free_limit on flip day keep all listings active; new creates above the limit require payment. Simplest for users; lowest churn risk.
- **(B) Hard-block above limit.** New creates require payment from day 1; existing N > limit listings stay active but seller cannot create new ones until they pay or archive.
- **(C) 30-day soft warning.** Active for 30 days; banner counts down; on day 31, behaviour matches (B).

**Recommendation:** (A). The spec says "test period earns trust"; punishing existing sellers on flip day breaks that contract. Confirm with product.

### 3.5.4 Counter reconciliation on flip day

Independent of (A)/(B)/(C):

- One-shot SQL on flip day: `UPDATE sellers SET listings_count = (live count from listings WHERE status=ACTIVE AND deleted_at IS NULL)`.
- After the reconciliation, the `Seller.listings_count` field is **abandoned for billing**. Either:
  - Drop the field (clean break).
  - Keep it as `lifetime_listings_count` and stop incrementing it — useful only as analytics, never as quota source.
- All future quota decisions read the live count.

### 3.5.5 Contested rules (open product questions)

- **Does `PENDING_GENERATION` count toward the limit?** Two views:
  - **Yes:** the seller has committed to publishing it; F1 latency is system-side; charging is fair.
  - **No:** the listing isn't visible to buyers yet; charging for invisible listings is wrong.
  Recommendation: **No, until ACTIVE.** Only ACTIVE + GENERATION_FAILED count.
- **Does `GENERATION_FAILED` count?** It's visible in B2C with a template description — so yes per spec. Confirm.
- **What if F1 takes hours?** Edge case: seller claims, status pending, day passes, status flips to active. Did the seller "create a listing today" or "yesterday"? For billing-purpose `created_at` ordering, use the original create timestamp, not the status-flip moment.
- **First-2-by-`created_at` rule for free slots:** does it use `Listing.created_at` (recommend) or the moment the seller first reached the limit? Recommend `created_at`. Confirm.
- **Can a seller swap their "first 2 free" by archiving an older one?** Yes — once free slots are derived from "first 2 ACTIVE by `created_at`", any of the seller's currently-active listings can occupy the slot, oldest first. Confirm.

## 3.6 Migration path for the broken counter

Independent of the test-period flip:

- **Today's bug:** the public `seller.listings_count` field is over-reported (includes paused/sold/expired/PG/GF). The dashboard live count is also over-reported (includes paused/sold/expired but excludes PG/GF when status filter is applied).
- **Two possible fixes today** (before any monetization activates):
  - **Fix A:** add status-aware decrement at every PATCH-status-change site. Three sites, ~10 lines.
  - **Fix B:** stop reading `seller.listings_count`; replace every read site (sellers.py:148, 177, 218, 458) with a live `count(*) WHERE status=ACTIVE AND deleted_at IS NULL` query.
- **Fix B is preferred** — simpler, no migration, no drift risk. The denormalised counter becomes dead-code; remove its writes too.

---

# 4. OPEN QUESTIONS (PRODUCT)

These are the non-technical decisions the spec deliberately defers. None can be silently assumed.

## 4.1 OTP / authentication

1. **C4 OTP delivery channel** — Telegram-bot (default, zero new infra) vs SMS via Eskiz (new integration, paid quota, ops cost). Recommendation: Telegram-bot for MVP; Eskiz as a Phase-2 upgrade. **DECISION REQUIRED before C4 PR2.**
2. **Should the claim-OTP `CacheKeys.otp` bug be fixed in scope of Block C, or as a standalone hotfix?** It's a one-line fix; recommend hotfix outside Block C to avoid coupling.
3. **Should the auth.py:957-1006 verify→create race be hardened?** Recommendation: yes, as part of the same hotfix as #2. Adds a wallet-creation hook later.
4. **`/auth/verify-seller-otp` for new-user creation vs `add-phone` flow** — confirm the new C4 endpoints are explicitly non-creating (never auth as a new user via add-phone).

## 4.2 Wallet (C3)

5. **Eager vs lazy Wallet creation?** Recommend lazy with idempotent INSERT. Confirm.
6. **Money storage as `BIGINT` (matching `Listing.price` precedent) vs `Numeric(18,2)` (industry standard)?** Recommend BIGINT. **For UZS this is exact; for USD, decide whether to model "cents" or "whole dollars".**
7. **Multi-currency wallets** — one wallet per (user, currency) or one per user with fixed currency? Recommend fixed-currency MVP, multi-currency Phase 2/3.
8. **`Subscription.object_id` — polymorphic FK or strict FK to listings?** Recommend polymorphic-ish (no FK constraint, typed by subscription.type) for flexibility.
9. **Refund semantics** — does a refund require the original transaction's status to flip to `refunded`, or do we keep the original `completed` and link a separate refund Transaction? Recommend the latter (cleaner audit trail; original is preserved).
10. **Click vs Payme priority** for Phase-2 integration. Doesn't gate C3 (both ship as stubs); blocks Phase-2 PR sequencing.
11. **Click/Payme webhook signature verification** — pin the algorithm at adapter creation time so the Protocol surface is right.
12. **Admin balance-adjustment audit trail** — single endpoint with mandatory reason? Or split into deposit/withdraw/correction with different gating? Recommend single with reason.
13. **Promotion / boost coupling** — `Listing.is_boosted` is a skeleton. When boost is paid, does it withdraw from the wallet or charge the provider directly? Defer to Phase 2 spec; out of C3.

## 4.3 Listing limit (C2)

14. **Option A (fix counter via hooks) vs Option B (kill counter, live-query)?** Recommend B.
15. **Grandfathering rule on flip day** — Option A (grandfather), Option B (hard-block), Option C (30-day soft)? Recommend A.
16. **Does PENDING_GENERATION count toward the limit?** Recommend **No**.
17. **Does GENERATION_FAILED count?** Per V2.0 spec: yes (visible in B2C with template). Confirm.
18. **First-2-free rule** — `Listing.created_at` (recommend) or first-active-at-flip-day? Confirm.
19. **Can sellers swap free slots by archiving older listings?** Recommend yes (live "oldest 2 active are free"). Confirm.
20. **What is the seller-seen counter on the dashboard during test period?** "Active: N (will be billable for N-2 from <date>)" or just "Active: N"? Spec is implicit; confirm.

## 4.4 Cross-cutting

21. **Does the product accept that, until SMS lands, seller flows that require phone verification (login, claim, add-phone) all depend on the seller having a Telegram account?** This is the operational reality today; documenting it explicitly avoids surprises.

---

# 5. RISK MATRIX

## 5.1 Production risks (live in code today)

| Risk | Severity | Where | Mitigation |
|---|---|---|---|
| `CacheKeys.otp()` `AttributeError` on claim-OTP fallback path | HIGH (latent) | `claims.py:150, 208, 235` vs `redis.py:39-83` | Hotfix: add `staticmethod otp(phone)` returning `f"otp:{phone}"`. Independent of Block C scope. |
| `auth.py:957-1006` verify→create race condition | MEDIUM | concurrent `/auth/verify-seller-otp` for same phone | Wrap user-creation in transaction with `INSERT … ON CONFLICT DO NOTHING` on `users.phone`. |
| `Seller.listings_count` over-reports for every paused/sold/expired/PG/GF listing | HIGH (silent) | `sellers.py:148, 177, 218, 458` | Replace reads with live `count(*)`. C2 deliverable. |
| `claim-OTP via SMS` is a TODO in `claims.py:157` referenced as if real | LOW | TODO comment | Either remove the comment + change UI copy, or build SMS. |
| `Listing.is_boosted` reads true in ranking but is never set anywhere | LOW (cosmetic / future) | `models.py:552-553`; reads in `buyer.py`, `search_index.py:127` | Acknowledge as Phase-2 feature; add admin set-boost endpoint at the same time as C3. |

## 5.2 Migration risks (introduced when Block C ships)

| Risk | Severity | Affects | Mitigation |
|---|---|---|---|
| `Seller.listings_count` field deletion or repurposing breaks downstream consumers (incl. frontend reading `seller.listings_count`) | MEDIUM | C2 | Audit every reader; replace before delete. Frontend reads dashboard `total_listings`, not the field directly — verify. |
| Wallet creation backfill (if eager) for existing users requires a one-shot script | MEDIUM | C3 | If lazy, eliminated. If eager, run during low-traffic; idempotent script. |
| Adding `user_phones` table (C4) and not backfilling primary phones from `User.phone` | HIGH | C4 → A1, A4 | Migration must include `INSERT INTO user_phones (user_id, phone, is_primary, …) SELECT id, phone, true, … FROM users WHERE phone IS NOT NULL`. |
| Postgres enum extensions for new transaction/subscription status need autocommit-block (Block A precedent) | MEDIUM | C3 | Re-use the `op.get_context().autocommit_block()` pattern proven in A8's migration. |
| `Click/Payme env vars` accidentally committed with values | HIGH | C3 settings | Use `.env.example` only; production via secret manager; pre-commit hook. |

## 5.3 Race-condition risks

| Risk | Severity | Where | Mitigation |
|---|---|---|---|
| **Concurrent withdraw on same wallet** | CRITICAL | C3 | `SELECT … FOR UPDATE` on Wallet row inside the withdraw service. Block A precedent: claim flow uses this pattern on source-listing rows. |
| **Webhook double-delivery from Click/Payme** | HIGH | C3 | `UNIQUE (idempotency_key)` constraint on `transactions`. Webhook handler upserts idempotently; second delivery returns the existing row. |
| **Listing-status PATCH race with claim-conversion** | LOW | C2 (live count) | Live `count(*)` is naturally consistent at read time; no race vector. |
| **Add-phone OTP verify race** (two devices verify the same incoming phone for two different users) | LOW | C4 | DB unique constraint on `user_phones.phone`. Second insert fails with 409. |
| **OTP-verify race with user-creation in login flow** (existing) | MEDIUM | auth.py:957-1006 | Hotfix per 5.1. |

## 5.4 UX / regression risks

| Risk | Severity | Where | Mitigation |
|---|---|---|---|
| Counter mismatch between "seller profile" and "seller dashboard" today | MEDIUM | already a bug | C2 fixes both; ship together. |
| User confusion when SMS fallback is mentioned in copy but unsupported | LOW | claims.py:157 + any UI copy | Copy review for "SMS" / "СМС" before any user-facing release. |
| Seller bills for PENDING_GENERATION listings perceived as "I haven't sold anything yet" | MEDIUM | C2 product question 16 | Recommend exclude PENDING_GENERATION from billable count; confirm with product. |
| Phone-collision suspicion (C5) misfires on legitimate multi-phone aggregations (C4) | HIGH | C5 spec already accounts for | Strict ordering: C4 ships first; C5 reads `user_phones`. |

## 5.5 Operational risks

| Risk | Severity | Mitigation |
|---|---|---|
| Telegram bot is the only OTP delivery channel; users without TG cannot register, claim, or add phones | MEDIUM | Document operational reality; ops handles edge cases manually until SMS integration. |
| Money bug in C3 wallet → non-recoverable | CRITICAL | Property-based concurrency tests; no production callers during test period; mandatory peer review on every withdraw/deposit PR. |
| Admin balance-adjust UI absence | LOW | Endpoint exists in C3; UI is Phase-2 ops tool. Acceptable. |

---

# Closing notes

This document is the **truth layer**. Specs, plans, and code that follow MUST cite this report when they make decisions whose justification is "the production codebase already does X" or "the codebase precedent for Y is Z".

**Three highest-impact findings:**

1. **OTP is Telegram-only.** Any spec / copy / product material claiming "SMS verification" is incorrect with respect to current code. C4 must default to Telegram-bot OTP.
2. **`Seller.listings_count` is broken.** Six observable bugs (3.1.1–3.1.3, plus the never-touched-on-status-transition hole). C2 should kill it, not fix it.
3. **`CacheKeys.otp` is a live latent bug** (not a Block C task, but adjacent): the claim-OTP fallback path will `AttributeError`. Hotfix recommended outside Block C scope.

Three product decisions block any Block-C code merge:
- C4 OTP channel (Telegram vs SMS).
- C2 Option A vs Option B (counter fix vs counter kill).
- C3 BIGINT vs Numeric(18,2) money storage.

Once those three answers are on file, the existing Block-C spec-kit can be picked up unchanged.
