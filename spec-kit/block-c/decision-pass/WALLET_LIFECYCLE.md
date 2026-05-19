# Wallet Lifecycle — Decision Pass

This document closes every wallet/transaction/subscription decision raised in [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) §2 and extends [`../hard/C3-wallet-architecture.md`](../hard/C3-wallet-architecture.md) with concrete state-machine and invariant decisions. Every choice is tied to a real-code precedent; deferrals are explicit.

## §0 Constraints inherited from production

The truth-layer audit established:

- **No wallet/transaction/subscription tables exist.** Greenfield.
- **No `Decimal` type used anywhere** in `backend/app/db/models.py`. `Listing.price` is `Integer` (whole UZS or whole USD).
- **`SELECT FOR UPDATE` row-level locks** are the established concurrency primitive — used by claim flow on source-listing rows.
- **`ON CONFLICT … DO UPDATE` additive merge** is the established idempotency primitive — A8's `source_metric` writeback uses it.
- **`AuditLog` is generic enough for transactions** — Block A's claim/reject already uses it via `entity_type='olx_listing'`/`'telegram_listing'` with old/new values JSONB.
- **No Protocol/ABC pattern** — codebase prefers config-driven if/elif (search backend toggle).
- **Currency enum exists** — `UZS`, `USD`. Used today only by `Listing.currency`.

These constraints — not invention — drive the decisions below.

---

## §1 Decision #6 — Lazy Wallet creation

🟢 **DECIDED: Lazy creation, idempotent insert.**

### Rationale

The codebase has **no eager-derived-row hooks** in user-creation. When a User is created at `auth.py:957-1006`, the only side effects are:

- (sometimes) Seller row creation
- token issuance

Adding "create Wallet" to that path means: every user who never reaches the paid phase carries a zero-row Wallet they don't need. At MVP scale (low thousands of users), the cost is small but real (DB rows, audit volume). At scale, larger.

Lazy creation matches the existing `ON CONFLICT DO NOTHING` idempotency pattern (Block A's source_metric). The wallet is created the first time it's needed — admin balance-adjust, future deposit webhook, or a future seller-side balance-read endpoint.

### Contract

```
get_or_create_wallet(db, user_id) -> Wallet:
    INSERT INTO wallets (user_id, current_balance, currency)
    VALUES (:uid, 0, 'UZS')
    ON CONFLICT (user_id) DO NOTHING;
    SELECT * FROM wallets WHERE user_id = :uid;
```

This is safe under concurrency: two simultaneous "first" calls both attempt INSERT; one wins via the UNIQUE(user_id) constraint, the other becomes a no-op via ON CONFLICT, and both subsequent SELECTs return the same row. **No locks needed for creation.**

### Invariants

- `wallets.user_id` is UNIQUE.
- `wallets.current_balance` defaults to 0; never NULL.
- `wallets.currency` defaults to `'UZS'`; never NULL.
- `wallets.created_at` is set once; never mutated.

### What this rules out

- **No backfill at C3 deploy time.** Existing users without paid activity have no wallet rows. This is the "explicit wallet" semantic.
- **No "create wallet on Seller creation".** Seller is just an additional role; wallet is per-User.

---

## §2 Decision #8 — Currency model: one-wallet-per-user, fixed UZS

🟢 **DECIDED: Single-currency wallet, UZS only in MVP.**

### Rationale

- Spec V2.0 prices everything in UZS (25 000 / 99 000 / 0).
- Currency enum exists with USD as a value, but **no exchange logic uses it for wallets**.
- Multi-currency wallets require: per-(user, currency) rows, currency conversion at deposit/withdraw boundaries, exchange-rate snapshotting, settlement currency policy. All Phase-2/3.

### Contract

- `wallets.currency` column exists for forward-compat but **is always `'UZS'` in MVP**.
- The `withdraw()` and `deposit()` services check currency match between Wallet and Transaction; **reject mismatch with 400** rather than auto-convert.
- USD enum value remains for `Listing.currency` and `Transaction.currency` (in case admin records a manual USD adjustment); not used in Wallet during MVP.

### What this rules out

- Multi-currency wallets (one user, two currency balances).
- Auto-conversion at deposit/withdraw.
- Cross-currency Subscription pricing.

All deferred to Phase 2.

---

## §3 Decision #9 — `Subscription.object_id` is polymorphic, no FK

🟢 **DECIDED: `object_id` is a UUID column with no foreign-key constraint; semantic is governed by `subscription.type`.**

### Rationale

- Cabinet subscription has no related listing; `object_id` is NULL.
- Listing-extra subscription pins to one listing; `object_id = listing.id`.
- Future subscription types (e.g., promotion bundles, multi-listing packs) may point to other entities. Adding a FK constraint locks us to one referenced table; polymorphic-style avoids that.

### Contract

```sql
object_id UUID NULL,
-- No FK. Validity is enforced at service layer:
--   IF type='cabinet' THEN object_id IS NULL
--   IF type='listing_extra' THEN object_id IS NOT NULL AND
--                                EXISTS (SELECT 1 FROM listings WHERE id = object_id)
```

### What this rules out

- Cascade delete from `listings` to `subscriptions`. If a Listing is deleted, its `Subscription(type='listing_extra')` rows become "orphaned with object_id pointing to a non-existent listing". The service layer treats this as `status='cancelled'` on the next read; admin cleanup script handles legacy rows.

This is acceptable because (a) Phase 2 Listing deletion is rare, (b) audit log preserves the original linkage, (c) explicit cascade FK introduces lock contention on listing deletes.

---

## §4 Decision #10 — Refund semantics

🟢 **DECIDED: Original transaction status flips `completed → refunded`; a separate refund Transaction is also inserted with `metadata.refund_of=<original_id>`. AuditLog row for both transitions.**

### Rationale

- **Auditability:** keeping the original row preserves "what actually happened on day X". Mutation alone loses the temporal sequence.
- **Refund chains:** a refund-of-a-refund is rare but possible (operator error). Linked-list via `metadata.refund_of` handles arbitrary chains.
- **Idempotency:** the refund Transaction has its own `idempotency_key` so duplicate refund webhooks don't double-credit.

### State machine

```
Original Transaction:
  pending → completed → refunded (terminal)
                     → (stays completed if no refund)
        ↓
        failed (terminal)

Refund Transaction (separate row):
  pending → completed (terminal)
        ↓
        failed (the refund itself can fail; original stays "refunded" awaiting reconciliation)
```

If a refund Transaction fails, the original stays `status='refunded'` but the wallet didn't actually credit back. This is a state worth flagging in admin alerts; an audit row records both the intent and the failure.

### What this rules out

- Soft-deleting refunded transactions. They stay queryable forever.
- Modifying `amount` on a refunded transaction. Transactions are append-mostly except for the documented status/completed_at fields.

---

## §5 Decision #11 — Click vs Payme priority

🟡 **RECOMMENDED: Click first; Payme second. Both ship as stubs in C3; live integration is Phase 2.**

### Rationale

- **Click has wider market share** in the Uzbekistan realtor segment (per market research; needs founder confirmation).
- **Click's API is mature** with well-documented webhook pattern — easier first integration.
- **Payme's API is comparable**; second integration validates the adapter pattern.

### Contract for C3 (today)

Both adapters ship as stubs:

```python
# backend/app/services/payment_providers/click.py
class ClickProvider:
    async def create_invoice(self, *, user_id, amount, currency) -> InvoiceResponse:
        raise NotImplementedError("Click integration: Phase 2")

    async def verify_callback(self, payload: dict, signature: str) -> CallbackResult:
        raise NotImplementedError("Click integration: Phase 2")

# backend/app/services/payment_providers/payme.py
class PaymeProvider:
    # same shape, same NotImplementedError stubs
```

Settings env-var slots added blank: `CLICK_MERCHANT_ID`, `CLICK_SECRET`, `CLICK_WEBHOOK_URL`, `PAYME_MERCHANT_ID`, `PAYME_KEY`, `PAYME_WEBHOOK_URL`. Production secrets injected via secret manager in Phase 2.

### Open product confirmation

**#11 PRODUCT-CALL** — confirm Click-first. Engineering ships either order; the order affects only Phase-2 sequencing.

---

## §6 Decision #12 — Webhook signature algorithms

🟡 **RECOMMENDED: Per-adapter; Protocol surface accepts raw signature only.**

### Rationale

- **Click uses MD5 + shared secret** (per public Click documentation).
- **Payme uses HMAC** (per public Payme documentation).

These are different algorithms; the Protocol can't dictate one. The right contract:

```python
class PaymentProvider(Protocol):
    async def verify_callback(self, payload: dict, signature: str) -> CallbackResult: ...
    # Implementation owns the algorithm choice; signature is opaque to the framework.
```

### What this rules out

- A shared "verify_signature(secret, payload, alg)" helper in the framework.
- Front-loading webhook security in C3 (when no real webhook arrives during test period).

---

## §7 Decision #13 — Admin balance-adjust endpoint

🟢 **DECIDED: Single endpoint `POST /admin/wallets/{user_id}/adjust` with type discriminator and mandatory reason.**

### Contract

```
POST /admin/wallets/{user_id}/adjust
Auth: admin only
Body: {
    "type": "grant" | "correction",
    "amount": <int, smallest unit, can be negative for correction>,
    "reason": "<required, free text>",
    "idempotency_key": "<optional UUID; if absent, generated server-side>"
}
Effect:
    1. get_or_create_wallet(user_id)
    2. SELECT FOR UPDATE on the wallet row
    3. INSERT Transaction(type='adjustment', amount, idempotency_key, ...)
    4. UPDATE wallet.current_balance = current_balance + amount
       (CHECK current_balance >= 0 → reject if grant would make it negative is N/A;
        for correction, the negative grant is rejected if it would underflow)
    5. INSERT AuditLog(actor_id=admin, entity_type='wallet',
                      entity_id=wallet.id,
                      old_values={"balance": old}, new_values={"balance": new, "reason": ...})
    6. Commit
Response: { "balance": <new>, "transaction_id": <uuid> }
```

### Invariants

- **Reason is mandatory.** Empty reason → 400.
- **Audit log entry is in the same transaction.** If the transaction rolls back, no audit row.
- **Balance never negative.** If `current_balance + amount < 0`, reject with 400.
- **Idempotency key is unique.** Same key = same outcome.

### Why single endpoint

Splitting into `grant` and `correction` doubles the surface for one bit of context (`type`). Single endpoint with discriminator is cleaner and matches REST principles for this kind of admin tool.

---

## §8 Decision #14 — `Listing.is_boosted` stays out of C3

🟢 **DECIDED: NO coupling between Wallet/Subscription and `is_boosted` in Block C scope.**

### Rationale

- The audit confirmed `is_boosted` is a **skeleton field** — declared at `models.py:552-553`, read by ranking logic, **never set anywhere**.
- The model comment is explicit: `# Promotion (Phase 2)`.
- Coupling C3 to it means designing the boost-purchase flow today; that's a Phase-2 feature with its own UX (boost duration, pricing, refund policy).

### What this means for C3

- C3 ships Wallet, Transaction, Subscription tables and services.
- C3 does NOT ship a `BoostPurchase` flow, a "boost a listing" endpoint, or any code that sets `is_boosted=true`.
- The first paid Subscription type at deploy is `cabinet` (99 000 UZS / month). `listing_extra` is the second type (25 000 UZS / month per extra listing). Both are about Subscription, not boost.

### What ships when boost is added (Phase 2)

A new Subscription type `boost` OR a separate `BoostPurchase` table. Decision deferred. C3's Subscription enum should accept either via the existing `type` column extension pattern (Block A's enum-extension precedent in `models.py:65-86`).

---

## §9 Transaction state machine — full reference

| State | Entry | Exit | Allowed transitions |
|---|---|---|---|
| `pending` | INSERT on deposit/withdraw initiation | provider response or admin action | → `completed` (success), → `failed` (failure), → never goes back to pending |
| `completed` | provider confirmed; balance updated | refund-of operation | → `refunded` (only via separate refund Transaction; original gets status flipped) |
| `failed` | provider rejected; balance NOT updated | terminal | (none) |
| `refunded` | original was completed; refund Transaction created and completed | terminal | (none) |

**Forbidden transitions:**
- `pending → pending` (no-op meaningless)
- `failed → completed` (can't un-fail; create new transaction)
- `completed → pending` (can't un-complete; would corrupt balance)
- `completed → failed` (impossible: balance is already updated)
- `refunded → completed` (use a new refund-of-refund chain)
- `refunded → failed` (refund cannot become a failure post-fact)

### State-machine enforcement

```python
# In wallet service:
ALLOWED_TRANSITIONS = {
    "pending": {"completed", "failed"},
    "completed": {"refunded"},
    "failed": set(),
    "refunded": set(),
}

def transition(tx: Transaction, new_status: str):
    if new_status not in ALLOWED_TRANSITIONS[tx.status]:
        raise InvalidTransition(f"{tx.status} → {new_status}")
    # ... do the transition with audit log
```

---

## §10 Withdrawal invariants

These rules MUST hold for every call to `wallet.withdraw()`:

| # | Invariant | Enforcement |
|---|---|---|
| W1 | Wallet exists for `user_id` | `get_or_create_wallet()` at start |
| W2 | Wallet row is locked for the duration of the operation | `SELECT … FOR UPDATE` |
| W3 | Withdraw amount > 0 | Schema validation |
| W4 | Withdraw amount ≤ current_balance | Service-layer check after lock |
| W5 | Currency match between wallet and transaction | Service-layer check |
| W6 | Idempotency: same `idempotency_key` → same Transaction row | Unique constraint on `transactions.idempotency_key` |
| W7 | Balance update and Transaction insert in same DB transaction | Wrap in `async with db.begin()` |
| W8 | AuditLog entry in same DB transaction | Inside the `async with` block |
| W9 | If service layer raises, DB transaction rolls back | Default behaviour |
| W10 | Caller receives the Transaction row (with new id) on success | Return value |

**Failure modes and their correct response:**

- Wallet not found (impossible after W1) → 500 (programmer error).
- Insufficient balance (W4 fails) → raise `InsufficientFunds`; HTTP 400 with code `wallet:insufficient_funds`.
- Currency mismatch (W5 fails) → raise `CurrencyMismatch`; HTTP 400 with code `wallet:currency_mismatch`.
- Duplicate idempotency_key (W6 fails) → return existing Transaction; HTTP 200 (idempotent success).
- Lock acquisition timeout (W2 fails) → raise `ConcurrentWalletAccess`; HTTP 503 with retry hint.
- AuditLog insert failure (W8 fails) → DB transaction rolls back; raise `AuditLogFailure`; HTTP 500.

---

## §11 Concurrency guarantees

### What's guaranteed

- **Two concurrent withdraws on same wallet** → serialised by `SELECT FOR UPDATE`. One wins, one waits. Neither double-spends.
- **Two concurrent webhook re-deliveries** → second hits unique-constraint on `idempotency_key`; returns existing Transaction.
- **Concurrent get_or_create_wallet** → ON CONFLICT NO-OP; one INSERT wins; both reads return same row.
- **Withdraw + simultaneous admin balance-adjust** → both grab the same SELECT FOR UPDATE; serialised. Whichever commits first sets the new balance; the other recomputes against the new balance.

### What's NOT guaranteed

- **Strict order of two concurrent withdraws.** Postgres lock-acquisition order ≠ request-arrival order. If "balance display" and "deposit success" race, the displayed balance may briefly reflect either. This is acceptable for read-after-write semantics over short windows.
- **Cross-wallet transactional consistency** (e.g., transfer from user A to user B). Out of MVP scope; if added, requires two-phase locking with deadlock detection.

---

## §12 Failure recovery

### Webhook timeout

Click/Payme webhooks may not arrive (network failure). The Transaction stays `pending` indefinitely until either:

- A subsequent retry from the provider arrives → idempotency key handles dedup.
- Manual admin intervention via the balance-adjust endpoint.

**No automatic timeout.** A pending Transaction is not "expired" by passage of time — only by an explicit terminal-state transition.

This is intentional: a 24-hour-old pending Transaction might still be redeemable by the provider on day 2.

### Service crash mid-withdraw

If the backend process dies between INSERT-Transaction and UPDATE-wallet, the DB transaction rolls back; nothing happens. On restart, no orphan rows.

If the backend dies AFTER UPDATE-wallet but BEFORE returning to caller, the DB transaction has committed. The caller receives a connection error but the withdraw succeeded. Caller's idempotency_key handles the retry safely.

### Database failover

`SELECT FOR UPDATE` requires the primary database. Read replicas are not eligible for wallet operations. If primary fails over, in-flight transactions roll back (Postgres standard); idempotency keys ensure retries don't double-spend.

---

## §13 Reconciliation strategy

### What needs reconciliation

For each Wallet, the invariant **balance = sum(completed credits) - sum(completed debits)** must hold.

A daily reconciliation job (Celery beat, low-traffic window):

1. For every Wallet row: compute `expected_balance` from the SUM(transactions.amount).
2. Compare to `wallet.current_balance`.
3. If mismatch: create AuditLog entry `entity_type='wallet_reconciliation_alert'`; admin reviews.

### When does this happen?

- **Bug-driven drift** is the primary risk: a code path commits a Transaction without updating the balance, or vice versa.
- **The DB enforces consistency at transaction-commit time** via the same DB-transaction wrapping (§W7). So in theory, drift only occurs from manual SQL or code bugs.
- **Reconciliation is a defence-in-depth** against unknown-unknowns; not a fix.

### What the reconciliation does NOT do

- Auto-correct balances. A mismatch is flagged for human review; admin uses the balance-adjust endpoint with reason `"reconciliation:transaction-id-X-missing"` to manually correct.

### What's deferred

- **Per-day balance snapshots** for time-travel queries — Phase 2 / 3 if/when wallet history becomes a feature.
- **Payment provider reconciliation** — comparing our Transactions against Click/Payme's reports — Phase 2.

---

## §14 Audit-log coupling

Every wallet state change writes an `AuditLog` row in the same DB transaction:

| Event | `entity_type` | `entity_id` | `action` | `old_values` | `new_values` |
|---|---|---|---|---|---|
| Wallet created (lazy) | `wallet` | wallet.id | `create` | `null` | `{balance: 0, currency: "UZS"}` |
| Transaction created | `transaction` | transaction.id | `create` | `null` | `{type, amount, status, ...}` |
| Transaction status change | `transaction` | transaction.id | `status_change` | `{status: old}` | `{status: new, completed_at?, reason?}` |
| Balance update | `wallet` | wallet.id | `balance_change` | `{balance: old}` | `{balance: new, transaction_id: <linked>}` |
| Subscription created | `subscription` | subscription.id | `create` | `null` | `{type, price, status, ...}` |
| Subscription status change | `subscription` | subscription.id | `status_change` | `{status: old}` | `{status: new, reason?}` |
| Admin balance-adjust | `wallet` | wallet.id | `admin_adjust` | `{balance: old}` | `{balance: new, amount, reason, admin_id}` |

### Pattern

```python
# Inside the same async with db.begin() block:
db.add(transaction)
db.add(audit_log)  # ← never separately
await db.commit()
```

If the audit add fails (rare), the transaction add fails too. **Either both, or neither.**

### Why not extend AuditLog with new columns?

The existing `old_values`/`new_values` JSONB is flexible enough. Adding columns increases migration complexity for marginal benefit. JSONB schema is documented in this file and in `WALLET_LIFECYCLE.md`.

---

## §15 Currency and precision

See [`MONEY_STORAGE_DECISION.md`](MONEY_STORAGE_DECISION.md) for the full rationale. Summary:

- **All money is BIGINT in smallest currency unit.**
- **For UZS:** smallest unit = 1 UZS (no fractional sub-unit in everyday use).
- **For USD:** smallest unit = 1 cent (so `$1.50 = 150`). Documented per-column.
- **Listing.price is Integer (existing).** Wallet/Transaction/Subscription align with this convention but use `BigInteger` for headroom (UZS at billions of units would overflow `Integer` at 2.1B).

---

## §16 What's deferred to Payments Phase 2 (NOT in C3)

| Item | Why deferred | Re-introduce when |
|---|---|---|
| Click webhook integration | Real money, real ops, ~1-2 dev-days | Phase-2 launch trigger fires |
| Payme webhook integration | Same | Phase-2 launch trigger fires |
| Topup UI for sellers | No user-side flow needed during test period | Phase-2 launch |
| Subscription auto-renewal Celery beat | No subscriptions billable yet | First paid subscriptions exist |
| Auto-archive listings on grace-period exhaustion | No paid listings yet | First listing-extra subscriptions |
| Boost purchase flow | Skeleton field; Phase-2 product surface | Promotion product spec lands |
| Multi-currency wallets | UZS-only MVP | Demand emerges from non-UZ users |
| Statement export, history UI | Phase-2 product surface | Phase-2 launch |
| Dispute / chargeback flow | Provider-specific; complex | When first dispute arrives |
| Reconciliation alert UI | Defence-in-depth; daily job runs first | First mismatch observed |

These are explicitly **OUT** of Block C. The C3 deliverable is the foundation only.

---

## §17 What's dangerous to implement early

| Anti-pattern | Why dangerous |
|---|---|
| Eager wallet on user-creation | Pollutes DB with empty wallets; backfill nightmare on schema change |
| Per-currency wallets in MVP | Doubles row count, doubles lock surface, no demand |
| Auto-conversion at deposit boundary | Locks us into a specific FX rate model; complicates audit; Phase 3 territory |
| Numeric(18,2) for money | Breaks codebase precedent; introduces float-rounding hazards; Decimal in Python ↔ Numeric in DB requires careful coercion |
| Single global lock for "any wallet operation" | Serialises all of monetization; kills throughput at scale |
| Cascading FK from Subscription to Listing | Listing delete becomes a long-locking subscription cascade; pollutes audit |
| Mutable Transaction rows beyond status/completed_at | Loses audit trail; opens replay bugs |
| Soft-deleting transactions | Same |

---

## §18 Cross-spec links

- [`DECISION_MATRIX.md`](DECISION_MATRIX.md) — master matrix.
- [`MONEY_STORAGE_DECISION.md`](MONEY_STORAGE_DECISION.md) — BIGINT vs Numeric rationale.
- [`../hard/C3-wallet-architecture.md`](../hard/C3-wallet-architecture.md) — full C3 spec.
- [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) §2 — wallet audit.
