# 12 — Deal Status + Final Price (Sold-Price Capture)

**Status:** NOT STARTED
**Complexity:** MEDIUM — one satellite table + new endpoint + UI modal + a single hard invariant (no SOLD without price); foundational for Phase 3.
**Vision-doc refs:** §5.1 ("Уровень 2" CRM), §5.3 (Real prices DB — strategic asset)
**Why now:** Phase 2. Schema-only first. Without this column, the Phase-3 data moat never starts accumulating — every month of delay = a month of lost data.

## Goal

When a seller marks a listing as sold, capture the **final closing price** and basic deal metadata. Over time these rows become the canonical source of truth for "real prices on the Uzbekistan real-estate market" — the cornerstone of the §5.3 monetisation strategy.

## Proposed data model

Add to `Listing`:

| Column | Notes |
|---|---|
| `sold_price` | BIGINT, nullable. Final agreed price in `currency`. |
| `sold_at` | Naive Tashkent timestamp. |
| `sold_currency` | Enum, default = `currency` (lets the seller record a USD-listed apartment that closed in UZS). |
| `sold_buyer_source` | TEXT, optional. Free-text "where did the buyer come from" — UcharMarket / OLX / personal contact / agent / other. Free text avoids forcing a taxonomy too early. |

Or — to keep `Listing` clean — a satellite table `ListingSale`:

| Column | Notes |
|---|---|
| `id` | UUID. |
| `listing_id` | UUID, unique. |
| `sold_price`, `sold_at`, `sold_currency`, `sold_buyer_source` | as above. |
| `created_by_user_id` | Audit. |
| `correction_history` | JSONB, optional — log of edits (last 10). |

Recommended: satellite table. Keeps `Listing` small, makes it easy to add fields like commission/co-broker later.

## Proposed API change

Replace the bare `POST /listings/{id}/status` with a transition that requires sold_price for `→ SOLD`:

```python
class MarkSoldRequest(BaseModel):
    sold_price: int = Field(..., gt=0)
    sold_currency: ListingCurrency
    sold_buyer_source: str | None = None
    sold_at: datetime | None = None  # default: now()

@router.post("/listings/{id}/sold")
async def mark_sold(...):
    ...
```

Old status endpoint keeps working for non-SOLD transitions.

## UI flow

Seller cabinet → listing detail → "Продано" button → modal:

1. Final price (number + currency selector, defaults to listing currency).
2. Where did the buyer come from? (RU/UZ chips: UcharMarket / OLX / Знакомые / Через агента / Другое).
3. Confirm.

After save:
- Listing → `SOLD` status.
- If channel autoposting is enabled, post a styled "✅ ПРОДАНО" card to the channel (see [`bot-channel-autopost`](../hard/bot-channel-autopost.md)).
- Bot DMs the seller a summary: cycle time (days from create → sold), contacts received, views.

## Behaviour & invariants

- **Cannot mark sold without sold_price** — the modal blocks. The seller's own analytics (oborot за месяц, средний цикл, conversion) only work if the field is non-null. The vision doc treats "self-deception destroys their own dashboard" as the main motivator for honest data — preserve that.
- **Editing after sold** — allowed for 24 h after sale, after that requires admin override. Discourages drift.
- **No buyer identity stored** — privacy. Just the price, time, and optional source.
- **Deletion** — soft only; sold history is part of the data moat.

## Strategic notes (from vision doc §5.3)

> Через 2-3 года UcharMarket будет единственным источником достоверных данных о реальных ценах сделок в Узбекистане. Потенциальные покупатели: банки (оценка залогов), застройщики (ценообразование), государство (налоговая база), международные инвесторы (due diligence).

This spec captures the raw rows. The downstream analytics product is [`real-prices-analytics`](../hard/real-prices-analytics.md).

## Acceptance criteria

- Seller can mark a listing sold with final price + currency + optional source.
- The listing transitions to `SOLD` and the sale row is persisted.
- Listing dashboard ("Performance") shows: created → sold cycle time, total views, total contacts.
- Aggregate dashboard exists (Phase 2.5+): "your sold inventory in last 30 days, ср. цена, ср. цикл".
- No way to set `SOLD` without a price (API + UI).
