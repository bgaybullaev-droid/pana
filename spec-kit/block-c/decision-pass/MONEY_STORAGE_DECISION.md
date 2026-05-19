# Money Storage — Decision Pass

This document closes Decision #7 from [`DECISION_MATRIX.md`](DECISION_MATRIX.md): **`BIGINT` (smallest currency unit) vs `Numeric(18,2)` (decimal-with-precision)**.

## §0 Constraints from production

The truth-layer audit established:

- `Listing.price` is `Integer` (not `Numeric`).
- `TelegramListing.price` and `OLXListing.price` are `Float` (parser uncertainty); coerced to `int(price)` on import via `crawler_service.py:611, 686`.
- **Zero `Decimal` types anywhere in `backend/app/db/models.py`.**
- `Currency` enum exists with `UZS` and `USD`. UZS is currently the only currency that appears in user-facing prices.
- Exchange rate is stored as integer fallback in settings (`exchange_rate_fallback: int = 12_800`).

The codebase has a clear precedent: **money is stored as integer, in whole UZS or whole USD units**. No fractional sub-unit handling exists.

---

## §1 Decision

🟢 **DECIDED: `BIGINT`, smallest currency unit, documented per column.**

For wallets:
- **UZS smallest unit = 1 UZS.** Integer storage; whole-currency only. (UZS has no everyday fractional sub-unit.)
- **USD smallest unit = 1 cent.** When (Phase 2/3) USD wallets are needed, $1.50 is stored as `150`. Document explicitly per column.

Column choice: `BigInteger` (Postgres `BIGINT` / SQLAlchemy `BigInteger`).

---

## §2 Rationale

### Codebase precedent

- `Listing.price` is `Integer` (sufficient at MVP scale for `1 UZS` precision).
- No Decimal/Numeric anywhere.

Introducing `Numeric(18,2)` for the wallet would create a precision mismatch:

```
Listing.price           = 250000 UZS (Integer)
Wallet.current_balance = Decimal("250000.00") UZS
Subscription.price     = Decimal("99000.00") UZS
```

That's two precision regimes coexisting. Future code reading `listing.price + 99000` may get a Python `int + Decimal = Decimal` result that surprises someone in three months.

Sticking with integer (BIGINT) keeps one precision regime: **everything is integer in smallest currency unit, full stop.**

### Why BIGINT and not INTEGER

- `Integer` (Postgres `INT` / 32-bit signed) max is 2,147,483,647 = 2.1 billion.
- 2.1 billion UZS = ~150,000 USD at current exchange. A future seller's lifetime transaction history could exceed this. A long-tail Wallet's `current_balance` could too.
- `BigInteger` (Postgres `BIGINT` / 64-bit signed) max is 9.2 × 10^18 — irrelevant overflow.

Cost of BIGINT vs INT: 4 extra bytes per column. At MVP scale, negligible. At any plausible scale, still trivial.

### Why not Decimal/Numeric

**Pro Decimal:**
- Industry standard for money.
- Explicit precision; no "is this UZS or kopeks?" ambiguity if you forget the convention.

**Con Decimal:**
- Mismatches existing Integer convention (Listing.price).
- Python `Decimal` ↔ SQLAlchemy `Numeric` requires careful coercion and locale-aware string handling.
- Float-rounding hazards at the JSON boundary unless explicit serialization.
- Doubles down on a convention this codebase doesn't use anywhere else.

**For UZS specifically:**
- UZS has no fractional sub-unit in everyday transactions. There's no "1 UZS = 100 tiyin" practice in retail.
- Decimal `(18, 2)` would store `99000.00` — the `.00` is always zero, wasted precision.

The integer convention is right for UZS. **For USD eventually, document the smallest-unit convention** (`$1.50 = 150`).

### Why per-column documentation matters

Column-level docstrings prevent the "is this UZS or kopeks?" trap:

```python
class Wallet(Base):
    current_balance: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
        comment="Wallet balance in smallest currency unit. UZS: whole UZS. USD: cents.",
    )
```

The `comment` parameter writes a `COMMENT ON COLUMN` in Postgres; visible in `\d+ wallets` and surfacing during admin SQL queries.

---

## §3 Per-column convention

| Table | Column | Type | Unit |
|---|---|---|---|
| `wallets` | `current_balance` | `BigInteger` | UZS: whole; USD: cents |
| `transactions` | `amount` | `BigInteger` | Same |
| `subscriptions` | `price` | `BigInteger` | Same |
| `listings` (existing) | `price` | `Integer` | Whole UZS / whole USD (existing convention; not changed) |

The pattern at every wallet column read site:

```python
balance_uzs = wallet.current_balance  # if wallet.currency == 'UZS', whole UZS
balance_usd_cents = wallet.current_balance  # if wallet.currency == 'USD', cents
# Display: format with `formatNumber(balance_uzs)` for UZS;
#          `formatPrice(balance_usd_cents / 100, "USD")` for USD.
```

---

## §4 Edge cases

### Negative balances are rejected, not stored

`CHECK (current_balance >= 0)` at the DB level. The `withdraw` service computes the new balance and rejects with `InsufficientFunds` if it would go below zero. The DB constraint is defence-in-depth.

### Overflow during arithmetic

`BigInteger + BigInteger` doesn't overflow at any plausible scale. UZS at 1 trillion = `10^12` — still has 7 orders of magnitude headroom.

### Conversion between currencies

Out of MVP scope. When Phase-2/3 multi-currency lands:

- A separate `currency_conversion` service rounds to whole units.
- Conversion records its own audit row with the rate used at conversion time.
- Round-half-to-even (banker's rounding) for fairness.

### Display formatting

Frontend's `formatNumber(value)` (Block A's `frontend/src/shared/lib/formatNumber.ts`) handles thousand-separators per locale. Currency-symbol decoration is per-locale.

For UZS: `99 000 сум` / `99 000 so'm` / `99 000 сўм`.
For USD: `$ 99,000` / `99 000 $`.

### Internal arithmetic vs display

Internal: integer math. `wallet.current_balance + transaction.amount` is always integer.
Display: format at the boundary. Never store a string-formatted price.

---

## §5 What this rules out

### Decimal everywhere

If a future contributor introduces `Decimal` for any new column, **flag it in code review.** The codebase precedent is integer. Diverging requires explicit Architecture Decision Record.

### Currency-aware columns

Don't add a `currency` column to every table. Use the wallet/transaction/subscription `currency` enum value as the source of truth for "which unit is this?". The interpretation is per-currency.

### Pre-emptive multi-currency

A multi-currency wallet model is feasible (one wallet per (user, currency)) but costs schema complexity. Defer to Phase 2/3 when there's a real user demand.

### Cents-everywhere convention

**For UZS, do NOT introduce kopek storage** ("100 kopeks per UZS") just to keep Decimal flavor. UZS doesn't have a fractional sub-unit in retail; storing as kopeks adds noise without precision benefit. Keep UZS as whole-unit.

For USD, **do** use cents — that's the standard and matches global practice.

---

## §6 Implementation notes

### SQLAlchemy

```python
from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

class Wallet(Base):
    __tablename__ = "wallets"
    # …
    current_balance: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        comment="Smallest currency unit. UZS: whole UZS. USD: cents.",
    )
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency),
        nullable=False,
        default=Currency.UZS,
    )
```

### Pydantic schema

```python
class WalletResponse(BaseModel):
    current_balance: int  # smallest currency unit
    currency: Literal["UZS", "USD"]
```

### Frontend type

```ts
type WalletResponse = {
  current_balance: number;   // smallest currency unit
  currency: "UZS" | "USD";
};
```

The frontend uses `formatNumber(balance)` for UZS; `formatPrice(balance / 100, "USD")` for USD.

---

## §7 Migration

The migration that creates `wallets`, `transactions`, `subscriptions` (Phase 1 of C3) declares all money columns as `BigInteger`. No conversion needed today — there are no existing rows.

When Phase-2/3 USD wallets land, the existing column stays `BigInteger`; the interpretation depends on `currency`. No migration.

---

## §8 Review checklist

When reviewing a wallet/transaction/subscription PR, verify:

- [ ] All money columns are `BigInteger`.
- [ ] Each money column has a `comment="…"` explicitly stating the unit.
- [ ] No `Decimal` or `float` in the column type.
- [ ] No string-formatted prices stored in the database.
- [ ] No conversion in the database layer (pure storage); conversions live in service code.
- [ ] Test fixtures use integer values, not strings.

---

## §9 Cross-spec links

- [`DECISION_MATRIX.md`](DECISION_MATRIX.md) — master matrix; this is decision #7.
- [`WALLET_LIFECYCLE.md`](WALLET_LIFECYCLE.md) — full wallet contract.
- [`../hard/C3-wallet-architecture.md`](../hard/C3-wallet-architecture.md) — C3 spec; uses these decisions.
- [`../TRUTH_LAYER_AUDIT.md`](../TRUTH_LAYER_AUDIT.md) §2.3.3 — Decimal-vs-Integer audit.
