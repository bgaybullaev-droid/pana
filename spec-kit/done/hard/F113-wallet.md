# 15 — Wallet (Ф-113)

**Status:** DONE
**Complexity:** HARD — Click + Payme integration, atomic ledger with idempotent webhooks, balance invariant, admin tooling.
**Vision-doc refs:** §10 (investment ask, line item Кошелек Ф-113)
**Why now:** Phase 2 prerequisite. Every monetisation feature ([`promotion-services`](../medium/promotion-services.md), Cabinet Pro tier, [`referral-program`](referral-program.md)) needs an internal balance ledger. Without this, those features can't ship.

## Goal

Internal currency-agnostic ledger that records: top-ups (from Click/Payme), spends (listing fees, boosts, subscriptions), and reward credits (from referrals). Users see a balance in the cabinet; admin sees a global ledger.

## Proposed data model

`Wallet`:

| Column | Notes |
|---|---|
| `id` | UUID. |
| `user_id` | FK CASCADE, unique (1:1 with User). |
| `balance_uzs` | BIGINT, default 0. Cents/sums depending on convention; recommend whole sums (no decimals — domain norm). |
| `created_at`, `updated_at` | Lifecycle. |

`WalletTransaction`:

| Column | Notes |
|---|---|
| `id` | UUID. |
| `wallet_id` | FK. |
| `amount_uzs` | BIGINT, signed. Positive = top-up / reward / refund. Negative = spend. |
| `kind` | Enum: `TOP_UP` / `LISTING_FEE` / `BOOST` / `BADGE` / `NOTIFY_PRIORITY` / `SUBSCRIPTION` / `REFERRAL_REWARD` / `REFUND` / `ADJUSTMENT`. |
| `external_payment_id` | Click/Payme transaction id; nullable for internal kinds. |
| `entity_type`, `entity_id` | What the spend was for (e.g. `listing`/`<uuid>`). Nullable. |
| `description` | Free text, RU. |
| `created_at` | Timestamp. |
| `created_by_user_id` | Audit. |

Constraint: `balance_uzs` must equal sum of all transaction amounts for that wallet. Enforce via a trigger or by *always* mutating the wallet through a service that does both writes in the same DB transaction.

## API surface

| Verb | Path | Purpose |
|---|---|---|
| GET | `/wallet` | Current user's balance + recent transactions. |
| POST | `/wallet/topup/click` | Initiates a Click payment. Returns a redirect URL. |
| POST | `/wallet/topup/payme` | Initiates a Payme payment. Returns a redirect URL. |
| POST | `/wallet/webhook/click` | Click → backend webhook (signed). On success: `TOP_UP` transaction. |
| POST | `/wallet/webhook/payme` | Same for Payme. |
| GET | `/admin/wallets` | Admin view: search, total volume, anomalies. |
| POST | `/admin/wallets/{user_id}/adjust` | Admin manual adjustment with reason. |

## Spend hooks

Service layer:

```python
async def spend(
    db: AsyncSession,
    *,
    user_id: UUID,
    amount: int,
    kind: WalletTransactionKind,
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    description: str = "",
) -> WalletTransaction:
    wallet = await get_or_create_wallet(db, user_id)
    if wallet.balance_uzs < amount:
        raise InsufficientFundsError()
    wallet.balance_uzs -= amount
    txn = WalletTransaction(
        wallet_id=wallet.id, amount_uzs=-amount, kind=kind, ...
    )
    db.add(txn)
    return txn
```

Called from:
- Listing publish (when seller exceeds free 2-listing quota): `spend(LISTING_FEE, 25_000)`.
- Boost / badge / priority purchases: see [`promotion-services`](../medium/promotion-services.md).
- Cabinet subscription rollover: `spend(SUBSCRIPTION, 99_000)` on monthly cron.
- Referral redemption: subtract a free slot from `ReferralReward.slots_consumed` instead of charging — see [`referral-program`](referral-program.md).

## Behaviour & invariants

- **Atomic** — every `spend` runs in a DB transaction; no partial state.
- **Negative balance forbidden** — `InsufficientFundsError` raised before wallet is decremented; UI prompts top-up.
- **Auditable** — every change has a transaction row. Balance is recomputable from transactions.
- **Idempotent webhooks** — Click / Payme deliver the same notification multiple times; key on `external_payment_id` to deduplicate.
- **Currency** — UZS only on day one. International cards / USD top-ups land in Phase 3.

## Frontend

Cabinet → "Кошелёк":
- Big balance card.
- Top-up button → currency entry → redirect to Click/Payme.
- Transaction history (paginated, filterable by kind).
- Quick-buy cards: "+1 объявление 25 000 sum", "+ Поднятие в топ 15 000 sum", etc.

## Acceptance criteria

- Top-up via Click and Payme lands successfully (mock webhook OK in dev).
- Spend on listing publish, boost, subscription works; balance never goes negative.
- Admin can adjust balance with audit trail.
- All wallet writes are atomic and idempotent.

## Open questions

- VAT / reporting — talk to finance before launch. Probably we issue receipts with `kind=TOP_UP` only.
- Refund policy — which kinds can be refunded automatically vs. require admin?
- Transaction retention — keep forever (small data, regulatory).
