# 03 — Master-Record Ranking Boost (Ф-108)

**Status:** DONE
**Complexity:** EASY — one-line ORDER BY change in the feed query — the only complexity is deciding the within-tier ordering.
**Vision-doc refs:** Section 3.2, Ф-108
**Why now:** Phase 1. One-line change. Gives claimed listings a perceived-quality boost without any new schema.

## What's done

- `Listing.master_record_id` self-FK exists ([03-listings](../../done/hard/03-listings.md)).
- `Listing.claimed_at` is stamped when a seller claims a listing ([04-claim-flow](../../done/medium/04-claim-flow.md)).

## What's missing

Two adjacent gaps in `backend/app/api/v1/listings.py:1186-1188` (the feed query):

1. **No dedup filter.** The query does NOT include `Listing.master_record_id.is_(None)`. Duplicate parsed listings render alongside their canonical master.
2. **No claim-rank boost.** The query orders by `Listing.is_boosted.desc(), sort_column.desc()` — claimed listings are not preferred over unclaimed parsed ones, contrary to the vision doc's "Мастер-запись имеет приоритет в выдаче над парсерными объявлениями".

## Goal

A claimed listing always ranks above an unclaimed one of similar age in the feed.

## Proposed change

Two small edits to the same query (`backend/app/api/v1/listings.py:1186-1188`):

```python
query = select(Listing).where(
    Listing.status == ListingStatus.ACTIVE,
    Listing.moderation_status == ModerationStatus.APPROVED,
    Listing.deleted_at.is_(None),
    Listing.master_record_id.is_(None),  # <-- 1. dedup filter
)
...
query = query.order_by(
    Listing.is_boosted.desc(),
    (Listing.claimed_at.is_not(None)).desc(),  # <-- 2. claim boost
    sort_column.desc(),
)
```

Effect: duplicates disappear; boosted listings on top (paid promotion), then claimed, then everything else, all newest-first within their tier.

## Considerations

- **Same-tier ordering** — within "claimed" tier, `created_at DESC` keeps the feed lively. If sellers complain that recently-claimed (but old-listing) records keep them at the top forever, switch to `claimed_at DESC` instead.
- **Paid listings outrank claim by design** — that's the vision doc's monetisation mechanic. Don't flip the order.
- **Per-tab impact** — the tabs spec ([F048-krutilka-three-tabs](../../not-started/medium/F048-krutilka-three-tabs.md)) should apply this ordering to every tab using the feed endpoint.

## Acceptance criteria

- Both edits land in `listings.py:1186-1188`.
- Existing tests still pass.
- Manual: a claimed listing of age N days ranks above an unclaimed listing of the same N days.
- Manual: a paid (`is_boosted=true`) listing still ranks above a claimed one.
- Manual: a duplicate parsed row (`master_record_id IS NOT NULL`) no longer appears in the feed; only the canonical master row renders.
