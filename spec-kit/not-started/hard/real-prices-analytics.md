# 19 — Real-Prices Analytics Export

**Status:** NOT STARTED
**Complexity:** HARD — materialised views, B2B API-key auth, quotas, anonymisation, multi-product packaging — and depends on a year of accumulated sold-price data.
**Vision-doc refs:** §5.3 (стратегический актив), §9 Phase 3
**Why now:** Phase 3. Depends on [`deal-status-and-final-price`](../medium/deal-status-and-final-price.md) having accumulated meaningful data (12+ months of sold-price rows). Defer until then. **But start collecting now** — the data moat compounds.

## Goal

Aggregate the per-listing sold-price rows into market-level analytics products that can be sold to banks (loan collateral valuation), developers (pricing), and the state (tax base). The vision doc treats this as the eventual moat — by year 2-3 UcharMarket should be the only authoritative source of real-transaction prices in Uzbekistan.

## Proposed products (sketch — actual scope set by sales)

1. **Per-district / per-property-type price index** — quarterly average and median sold-price. Public endpoint (free) for marketing; CSV export gated behind paid tier for B2B clients.
2. **Days-on-market index** — average time from publish → sold per district / property type.
3. **Discount-from-asking** — average gap between listed price and sold price.
4. **Per-developer / per-residential-complex pricing trends** — ties into the housing-complexes module that already exists in the codebase.
5. **API access** — read-only API for B2B subscribers. Auth via API key, rate-limited.

## Proposed data model

No new core columns — the analytics live as **materialized views** computed from `Listing` + `ListingSale` (see [`deal-status-and-final-price`](../medium/deal-status-and-final-price.md)):

```sql
CREATE MATERIALIZED VIEW mv_district_price_index AS
SELECT
    listing.district,
    listing.property_type,
    date_trunc('quarter', sale.sold_at) AS quarter,
    COUNT(*) AS sample_size,
    AVG(sale.sold_price) AS avg_price,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY sale.sold_price) AS median_price,
    AVG(sale.sold_price - listing.price) AS avg_discount,
    AVG(EXTRACT(EPOCH FROM (sale.sold_at - listing.created_at)) / 86400) AS avg_days_on_market
FROM listings listing
JOIN listing_sales sale ON sale.listing_id = listing.id
GROUP BY 1, 2, 3;
```

Refreshed nightly via celery beat.

## API surface

| Verb | Path | Purpose |
|---|---|---|
| GET | `/analytics/price-index` | Public. Free per-district / per-property quarterly index. |
| GET | `/analytics/days-on-market` | Public. Free overview. |
| GET | `/analytics/raw-export` | B2B paid tier; CSV export with row-level (anonymised) data. API-key auth. |
| GET | `/analytics/api/v1/*` | B2B paid tier; programmatic access. |

`B2BAPIKey`:

| Column | Notes |
|---|---|
| `id`, `client_name`, `key_hash`, `monthly_quota`, `requests_used`, `created_at`, `expires_at` |

## Behaviour & invariants

- **Privacy** — no listing identifies its seller in analytics output. Aggregations only. Raw export anonymises seller info.
- **Sample-size threshold** — buckets with < 5 sales are suppressed (avoid identifiability + noisy averages).
- **Refresh cadence** — nightly. Real-time analytics is not a goal.
- **Versioning** — analytics endpoints versioned (`/analytics/api/v1/...`) for stability across years.

## Acceptance criteria

- Materialised views populated from `ListingSale` data.
- Public price-index endpoint returns sane numbers when sold data exists; suppresses sparse buckets.
- B2B API-key auth + quota enforcement.
- CSV export pipeline.

## Open questions

- Product packaging — annual subscriptions for banks vs. per-query for one-off due-diligence? Sales-led.
- Government integration — separate spec when it becomes concrete; likely involves data residency + audit trail.
- Open-data publication — quarterly press release with public summary as marketing? Probably yes.
