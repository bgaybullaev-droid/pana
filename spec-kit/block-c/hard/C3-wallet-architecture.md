# C3 — Wallet, Transaction, Subscription architecture (Phase-1 prep)

**Status:** NOT STARTED — zero billing infrastructure in the repo. `AuditLog` exists and can be reused. `Listing.is_boosted` is a skeleton field with no payment coupling. Currency enum has UZS+USD but no wallet/subscription model. No Click/Payme adapters, no env vars.
**Complexity:** HARD — three new tables with foreign keys, an idempotent withdraw service, audit-log integration, adapter stubs, multi-currency awareness, refund/grace-period semantics. Multi-table greenfield with strong invariants.
**Block-C V2.0 ref:** C3.
**Why now:** the spec's principle is "the structure must be right on day 1; reshuffling tables when monetization activates is much more expensive than building right now". This is the foundation other Phase-2 work sits on.

## What's done

- **`AuditLog` model** at `backend/app/db/models.py:1316-1345` — generic, has `entity_type`, `entity_id`, `action`, `old_values`/`new_values` (JSONB), `ip_address`, `user_agent`, `user_id`, `created_at`. Already used for claim/reject (Block A). **Re-usable** for transaction state changes by setting `entity_type='transaction'`.
- **`Currency` enum** at `models.py:103-107` — `UZS`, `USD`. Used today only by `Listing.currency` (default USD).
- **`Listing.is_boosted`** at `models.py:552` and `boost_until` at line 553 — model fields exist, no admin endpoint, no payment coupling. Comment in code says `"Promotion (Phase 2)"` — explicit deferral.
- **Settings.py** has `exchange_rate_api_url` (CBU UZ) and `exchange_rate_fallback: int = 12_800` for UZS↔USD conversions.
- **No conflicting code** to delete — fully greenfield.

## What's missing

1. **No `Wallet` model.** No table, no field on User/Seller for current balance.
2. **No `Transaction` model.** No history of money movement.
3. **No `Subscription` model.** No way to express "this seller has the Cabinet subscription" or "this listing is paid this month".
4. **No idempotent withdraw service.** Spec wants this implemented and tested in Phase 1, never called in prod.
5. **No payment-provider adapters.** Click and Payme have no Python clients in the repo, no settings env vars (`CLICK_*`, `PAYME_*` — none).
6. **No audit-log of transaction state changes.** AuditLog can be used; the wiring needs to be written.
7. **No grace-period logic** for negative balance / failed renewal.
8. **No admin balance-adjust path.** Spec wants admins to be able to grant balance manually; that endpoint doesn't exist.
9. **No coupling to C1/C2.** When the test-period flag flips, nothing connects "seller has 3+ listings" to "withdraw 25 000 UZS from wallet".
10. **No coupling to `Listing.is_boosted`.** Today is_boosted is settable only at the model layer; no admin path; no transaction logged.

## Path to DONE

### Step 1 — schema

Migration `prj_wallet_billing.py`:

```python
# wallets — one per user; UZS by default
op.create_table(
    "wallets",
    sa.Column("id", UUID, primary_key=True, default=uuid4),
    sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"),
              nullable=False, unique=True),
    sa.Column("current_balance", sa.Numeric(precision=18, scale=2),
              nullable=False, server_default="0"),
    sa.Column("currency", sa.Enum("UZS", "USD", name="currency", create_type=False),
              nullable=False, server_default="UZS"),
    sa.Column("version", sa.Integer, nullable=False, server_default="0"),  # optimistic lock
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(),
              onupdate=sa.func.now()),
)

# transactions — append-mostly; status mutates but each row is preserved.
# All money movement goes through here.
op.create_table(
    "transactions",
    sa.Column("id", UUID, primary_key=True, default=uuid4),
    sa.Column("wallet_id", UUID, sa.ForeignKey("wallets.id", ondelete="RESTRICT"),
              nullable=False, index=True),
    sa.Column("type", sa.Enum("deposit", "withdrawal", "refund", "adjustment",
              name="transaction_type"), nullable=False),
    sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column("currency", sa.Enum("UZS", "USD", name="currency", create_type=False),
              nullable=False),
    sa.Column("status", sa.Enum("pending", "completed", "failed", "refunded",
              name="transaction_status"), nullable=False, server_default="pending"),
    sa.Column("external_payment_id", sa.String(128), nullable=True),
    sa.Column("subscription_id", UUID, sa.ForeignKey("subscriptions.id",
              ondelete="SET NULL"), nullable=True),
    sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
    sa.Column("idempotency_key", sa.String(64), nullable=True, unique=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now(), index=True),
    sa.Column("completed_at", sa.DateTime, nullable=True),
)
op.create_index("idx_tx_wallet_status", "transactions", ["wallet_id", "status"])
op.create_index("idx_tx_external_payment_id", "transactions",
                ["external_payment_id"], unique=False)

# subscriptions — Cabinet subscription or extra-listing slot
op.create_table(
    "subscriptions",
    sa.Column("id", UUID, primary_key=True, default=uuid4),
    sa.Column("user_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"),
              nullable=False, index=True),
    sa.Column("type", sa.Enum("cabinet", "listing_extra",
              name="subscription_type"), nullable=False),
    sa.Column("object_id", UUID, nullable=True),  # listing_id when type=listing_extra
    sa.Column("price", sa.Numeric(precision=18, scale=2), nullable=False),
    sa.Column("currency", sa.Enum("UZS", "USD", name="currency", create_type=False),
              nullable=False, server_default="UZS"),
    sa.Column("billing_cycle", sa.Enum("monthly", "yearly",
              name="billing_cycle"), nullable=False, server_default="monthly"),
    sa.Column("status", sa.Enum("active", "paused", "cancelled", "expired", "grace",
              name="subscription_status"), nullable=False, server_default="active"),
    sa.Column("starts_at", sa.DateTime, nullable=False),
    sa.Column("ends_at", sa.DateTime, nullable=True),
    sa.Column("next_billing_at", sa.DateTime, nullable=True, index=True),
    sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(),
              onupdate=sa.func.now()),
)
op.create_index("idx_sub_user_type", "subscriptions", ["user_id", "type"])
```

`Numeric(18, 2)` to avoid floating-point money bugs. `idempotency_key` is unique; the idempotent withdraw service uses it.

### Step 2 — SQLAlchemy models

`backend/app/db/models.py` — `Wallet`, `Transaction`, `Subscription` classes mirroring the migration. Relationships: `User.wallet` (one-to-one), `Wallet.transactions`, `Subscription.transactions`.

### Step 3 — wallet service (idempotent)

`backend/app/services/wallet.py`:

```python
async def withdraw(
    db: AsyncSession,
    wallet: Wallet,
    amount: Decimal,
    *,
    purpose: str,        # "subscription:cabinet", "listing:extra:<id>"
    subscription_id: Optional[UUID] = None,
    idempotency_key: str,
) -> Transaction:
    """
    Charge `wallet` by `amount`. Idempotent on `idempotency_key`.
    Atomic: lock wallet (SELECT FOR UPDATE), insert transaction, update balance,
    write audit log. Raises InsufficientFunds if balance < amount.
    Never called in prod during test period.
    """
```

Tests: idempotency under concurrent calls; insufficient funds; happy path. **Run in CI; never invoked from production routes during test period.**

### Step 4 — deposit service

`async def deposit(db, wallet, amount, *, source, external_payment_id, idempotency_key) -> Transaction`. Same idempotency pattern. Used by webhooks (Click/Payme) when those land in Phase 2.

### Step 5 — adapter stubs

`backend/app/services/payment_providers/click.py` and `backend/app/services/payment_providers/payme.py`:

```python
class PaymentProvider(Protocol):
    async def create_invoice(self, user_id: UUID, amount: Decimal, currency: str) -> InvoiceResponse: ...
    async def verify_callback(self, payload: dict, signature: str) -> CallbackResult: ...

class ClickProvider:
    async def create_invoice(self, ...) -> InvoiceResponse:
        raise NotImplementedError("Click integration deferred to Phase 2")

class PaymeProvider:
    async def create_invoice(self, ...) -> InvoiceResponse:
        raise NotImplementedError("Payme integration deferred to Phase 2")
```

The interface is committed; the bodies are stubs that raise `NotImplementedError` if ever called. Settings env vars (`CLICK_MERCHANT_ID`, `CLICK_SECRET`, `PAYME_MERCHANT_ID`, `PAYME_KEY`) are added but blank — Phase-2 work activates them.

### Step 6 — audit-log integration

Each call to `withdraw()` / `deposit()` / `refund()` / admin-adjust writes an `AuditLog` row with `entity_type='transaction'`, `entity_id=transaction.id`, `old_values`/`new_values` capturing status transitions. Helper:

```python
async def log_transaction_state_change(
    db: AsyncSession, tx: Transaction,
    old_status: TransactionStatus, new_status: TransactionStatus,
    actor_id: UUID, reason: str
):
    db.add(AuditLog(
        user_id=actor_id,
        entity_type="transaction",
        entity_id=tx.id,
        action=f"status_change",
        old_values={"status": old_status.value},
        new_values={"status": new_status.value, "reason": reason},
    ))
```

### Step 7 — admin balance-adjust endpoint

`POST /admin/wallets/{user_id}/adjust` (admin auth required):

```json
{ "amount": 50000, "reason": "compensation for outage on 2026-05-08" }
```

Inserts a Transaction with `type=adjustment`, writes AuditLog with admin's `user_id`. Reason is mandatory.

**Skeleton only** — endpoint exists with admin guard, returns 200 on a no-op or stores the row. Whether it's hidden behind a UI today is a product call.

### Step 8 — wallet auto-creation hook

When does a Wallet row exist for a user? Two strategies:

- **Lazy:** create on first deposit. Simpler; users without wallets just don't have one.
- **Eager:** create immediately on user registration.

**Recommendation: lazy.** A user who never reaches paid phase never has a wallet row. This avoids massive backfill on existing users.

The `withdraw()` and `deposit()` services include `get_or_create_wallet(user_id)` at the start.

### Step 9 — five-question architecture review

Spec requires the architect can answer five questions without schema change:

1. **Pre-paid 3 months of Cabinet:** insert a `Subscription` with `next_billing_at = now() + 90d`, three Transactions (one each month) — or a single Transaction covering 3 months and `next_billing_at = now() + 90d`. Either works. ✅
2. **5 paid listings + Cabinet — billing order:** monthly, on `next_billing_at` per subscription. Independent. Order: query all subscriptions where `next_billing_at <= now()`, withdraw in DB order. ✅
3. **Failed withdrawal — what happens:** subscription enters `status='grace'`; configurable `grace_period_days` (e.g. 7); after grace, status=`paused`; relevant Listings auto-archived. ✅
4. **Roll back an erroneous transaction:** insert a `refund` Transaction with `type='refund'` referencing the original via `metadata.refund_of`. Original's status flips to `refunded`. AuditLog records both. ✅
5. **Promo code / discount in Phase 2:** add `discount_id` and `discount_amount` to `Subscription` or `Transaction.metadata`. No schema change required if we use metadata; add columns later if needed. ✅

All five answers stand without schema change.

## Behaviour & invariants

- **All money in `Numeric(18,2)`**, no floats.
- **Append-mostly Transaction.** Existing rows mutate only `status` and `completed_at`; everything else is immutable.
- **Idempotency by `idempotency_key`.** Same key → same transaction. Webhook re-delivery doesn't double-charge.
- **Optimistic locking on Wallet.** `version` column incremented on every balance update; concurrent updates one of them retries.
- **`SELECT FOR UPDATE` on wallet** during withdraw/deposit; serialises balance edits per wallet.
- **AuditLog every state transition.** No state change without an audit row.
- **Admin adjustment requires reason.** Empty reason → 400.
- **Wallet never goes negative** without grace mode. Insufficient funds → withdraw raises before mutation.
- **Currency stays UZS.** USD support is schema-ready but unused; Phase-2 / Phase-3 work.
- **No Listing field changes** in C3. `is_boosted` stays a skeleton; coupling with payment is its own task in Phase 2.

## Architecture notes

- The `withdraw` / `deposit` services are **the only** code that mutates `Wallet.current_balance`. Lock here; no other path.
- Click/Payme adapters use `PaymentProvider` Protocol; the rest of the system depends on the protocol, not concrete classes — easy to swap.
- The `transaction.subscription_id` FK lets us answer "what did this charge belong to" without joining through metadata.
- Cabinet subscription: `type='cabinet'`, no `object_id`. Listing-extra: `type='listing_extra'`, `object_id=listing.id`.

## Upstream dependencies

- **AuditLog** (Block A) — done.
- **Currency enum** — done.
- **A1, A4, A7, A8** — none directly required.

## Downstream dependencies

- **C1** — page renders disabled CTAs that *will* call `wallet.deposit` and `subscription.subscribe`. Today they no-op modal; Phase 2 wires them.
- **C2** — `check_can_create_listing` consults `Subscription` table when paid phase activates.
- **D4** (planned, not in C) — bot autopost gated by `Subscription(type='cabinet', status='active')`.
- **F-block** — none.

## Migration / schema implications

- Three new tables (`wallets`, `transactions`, `subscriptions`) with FK to `users` + `listings`.
- New enums: `transaction_type`, `transaction_status`, `subscription_type`, `subscription_status`, `billing_cycle`.
- `Currency` enum reused (already exists).
- **Backwards-compatible.** No existing rows touched; no existing endpoints break.

## API implications

- New endpoint set, all admin-auth or future-user-auth:
  - `POST /admin/wallets/{user_id}/adjust` — implemented now (Step 7).
  - All seller-facing endpoints (`POST /wallet/topup`, `GET /wallet/balance`, `POST /subscriptions`, etc.) — **explicitly out of scope for C3.** Phase-2 work.
- No changes to existing endpoints.

## Crawler / bot implications

- **None today.** When D4 (bot autopost) lands, it consults `Subscription`.

## AI / F-block implications

- **None.**

## SEO implications

- **None.**

## Localization implications

- Backend error codes only (no user-facing text in C3 routes today). Frontend uses C1's i18n for the disabled-CTA modal.
- When admin balance-adjust gains a UI, that copy goes through `admin` namespace.

## Infra / deploy implications

- Database migration deploys with the next release. Tables are empty at create — no risk window.
- Settings env vars added (blank): `CLICK_MERCHANT_ID`, `CLICK_SECRET`, `CLICK_WEBHOOK_URL`, `PAYME_MERCHANT_ID`, `PAYME_KEY`, `PAYME_WEBHOOK_URL`. Add to `backend/.env.example` so deploys carry the slot.
- **No production credentials added yet.** Click/Payme integration coordination is Phase-2 work.

## Edge cases

- **Existing users have no wallet** at deploy time. Lazy-create on first deposit; tested explicitly.
- **Currency mismatch.** Wallet UZS, transaction USD — reject with 400 in service layer; no auto-conversion in C3 (Phase-2 problem).
- **Duplicate webhook delivery.** Idempotency key catches it; second insert hits the unique constraint, surface a clean response.
- **Negative balance via concurrent withdrawals.** Lock + version → one of two callers retries.
- **Refund of a refund.** `metadata.refund_of` chain; allowed but rare. Audit row for each link.
- **Subscription type mismatch.** `type='listing_extra'` with `object_id=NULL` → invalid; constraint check at service layer (CHECK constraint optional, depends on DB).
- **Subscription paused mid-month.** `ends_at` set to now; `next_billing_at` cleared. No proration in MVP.
- **Currency-unaware reporting.** Aggregate views must group by currency; never sum across.

## Operational risks

- **Money bugs are non-recoverable.** A buggy idempotency check doubles a charge. **Strong unit + integration tests for `withdraw` are mandatory.** Property-based testing recommended.
- **Audit log volume.** Every transaction state change writes a row; reasonable at MVP scale.
- **Click/Payme webhooks need IP allowlist + signature verification.** Phase-2 work, but the adapter Protocol must accept a `signature` param.
- **Refund flows are legal-grade.** Test against the providers' sandbox before any real money flows.
- **Test-period flag flip is a billing event.** When `test_period_active=false` is set, sellers begin to be charged. The flip must be explicit (admin action; AuditLog row), not a silent config push.

## Rollout strategy

- **Phase-1 (this spec):** ship schema, services, adapter Protocol, admin-adjust endpoint. **Test-only invocation.** Production never calls withdraw/deposit.
- **Phase-2 (out of C3):** wire Click + Payme webhooks; turn on real deposits. Then turn off `test_period_active` once Phase-1 has been observed for the spec'd 60 days.
- **Rollback:** the migration is additive (adds tables/enums); rollback drops them. No data loss because no rows exist in production during test period.

## Acceptance criteria

- Migration `prj_wallet_billing.py` creates the three tables + enums; `alembic upgrade head` succeeds; `alembic downgrade -1` is reversible (because tables are empty in production).
- `Wallet`, `Transaction`, `Subscription` SQLAlchemy classes exist with relationships.
- `wallet.withdraw()` and `wallet.deposit()` services exist with full unit tests proving idempotency, atomicity, insufficient-funds, and concurrency.
- `PaymentProvider` Protocol + Click/Payme stubs exist; both raise `NotImplementedError`.
- `POST /admin/wallets/{user_id}/adjust` works; AuditLog row created on adjust.
- All five "architect can answer without schema change" questions are answerable from the design.
- No production endpoint invokes `withdraw` or `deposit` (verified by grep).

## Recommended PR split

- **PR1** — migration + models. Pure schema; no behaviour change.
- **PR2** — services (`wallet.py`) + tests + adapter Protocol + Click/Payme stubs.
- **PR3** — admin balance-adjust endpoint + AuditLog wiring + tests.
- **PR4** — settings env-var slots, `.env.example` updates.

## Estimated complexity

- Schema + models: ~0.5 day BE.
- Services + tests: ~2 days BE.
- Adapter stubs + admin endpoint: ~0.5 day BE.
- AuditLog wiring + tests: ~0.5 day BE.

Total ~3.5 dev-days BE. Front-end and ops work explicitly out of scope.

## Open questions

1. **Wallet creation strategy** — lazy (recommended) or eager? If lazy, do we want a one-shot script when `test_period_active` flips to false to create wallets for everyone?
2. **`Subscription.object_id` typing** — should this be a polymorphic FK (today: just listing_id) or a proper FK to `listings`? Recommend polymorphic-ish (typed by `subscription.type`), no FK constraint to keep flexibility for future subscription types.
3. **`Subscription.status='grace'` length** — config knob? Spec mentions 7 days as a baseline.
4. **Click/Payme prioritisation** — which one first in Phase 2? Doesn't affect C3 (both stubs ship), but affects PR ordering for Phase 2.
5. **Multi-currency wallets** — one wallet per (user, currency) or one per user with a fixed currency? Spec says single UZS today, but the schema allows multi. Recommendation: one wallet per user, fixed currency; revisit if USD wallets become needed.
6. **Refund atomicity with provider.** When a refund is initiated, does Click/Payme's refund API need to succeed *before* we mark our transaction as refunded? Yes, per standard practice. Document.
7. **Metadata schema** — JSONB is flexible; we should publish a schema doc for `metadata.refund_of`, `metadata.discount_id`, etc., so future code uses consistent keys.

## References

- `backend/app/db/models.py:1316-1345` — `AuditLog` (re-used for transaction state changes).
- `backend/app/db/models.py:103-107` — `Currency` enum.
- `backend/app/db/models.py:552` — `Listing.is_boosted` (related, deferred).
- `backend/app/core/config.py` — settings file to extend.
- `backend/app/services/` — services dir.
- `backend/alembic/versions/` — migrations dir; next revision id following `pri_source_metric_notified`.
- [C1](../medium/C1-tariff-display.md), [C2](../medium/C2-free-limit-logic.md) — UI consumers in Phase 2.
- [A8](../../block-a/medium/A8-channels-management.md) — admin endpoint pattern to mirror.
