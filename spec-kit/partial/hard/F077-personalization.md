# 02 — Personalisation: Interest Vector (Ф-77 / Ф-78)

**Status:** PARTIAL
**Complexity:** HARD — Phase-1 collection table, Phase-2 scoring algorithm, Phase-3 ML iteration; scope is open-ended and the data design has long downstream consequences.
**Vision-doc refs:** Section 4 (three-tier personalisation)
**Why now:** Phase 1 fini­shes with this still chronological — it's a Phase-2 feature, but the data-collection layer (Tier 3) should start in Phase 1 so we have signal by the time we build the model.

## What's done — verified

- **Tier 1 (explicit prefs)** — `NotificationPreferences` filters cover the onboarding-prefs intent. UI: `frontend/src/modules/buyer/pages/notification-settings/`.
- **Tier 2 (active actions)** — `Favorite`, `SavedSearch`, `UserFollowsSeller`, `CommentLike` all exist and write on the corresponding actions.
- **Tier 3 (implicit signals)** — only the aggregate `Listing.views_count` is bumped at `backend/app/api/v1/listings.py:1821`. No per-user history, no dwell, no session attribution.

## What's missing — exact map

1. **No per-user view history.** No `UserListingView` (or any equivalent event) table exists. Zero references in models, migrations, or API.
2. **No `POST /listings/{id}/view` endpoint.** Frontend has nowhere to push an explicit view + dwell event.
3. **No dwell signal on the swiper.** Frontend never measures time-on-object.
4. **No anonymous-then-attributed session bridge.** Open question in this spec; not designed.
5. **Self-view exclusion bug.** `views_count += 1` at `listings.py:1821` runs unconditionally — sellers inflate their own metric on every preview. Cross-cuts with [`../easy/seller-dashboard-counters.md`](../easy/seller-dashboard-counters.md), which also calls this out.
6. **No scoring pipeline / recommendation feed.** Phase-2 work; depends on the data above.

## Goal (Phase 2 target)

A Recommended feed that orders listings by a per-user score derived from explicit prefs + actions + implicit signals.

## Proposed data model (Phase 1 — collect signal only)

**Canonical name: `ListingViewEvent`** (aligned with the broader event-row design in `../easy/seller-dashboard-counters.md`, which proposes the same shape with an `event_type` discriminator). One table covers both personalisation and dashboard analytics — no schema-naming collision.

| Column | Notes |
|---|---|
| `id` | UUID. |
| `user_id` | FK CASCADE. Nullable for anonymous views. |
| `listing_id` | UUID, no FK (same convention as Favorites). |
| `event_type` | Enum: `VIEW` / `CONTACT` / `SHARE`. `VIEW` is the personalisation feed; the others ride the same table. |
| `viewed_at` | Naive Tashkent timestamp. |
| `dwell_ms` | Bigint, nullable. Set by frontend on swipe-away. Only meaningful for `VIEW`. |

Indexes: `(user_id, viewed_at DESC)` for reads; partial index on non-null `user_id` for the recommendation worker; `(listing_id, event_type, viewed_at)` for the seller dashboard rollups.

## Proposed API surface

- `POST /listings/{id}/view` — `{dwell_ms?: int}`. Idempotent enough — multiple calls for the same listing/user/day collapse server-side (one row per `date(viewed_at)`).

## Proposed scoring (Phase 2)

Simple linear scoring as a starting point (no ML):

```
score = w_view    * recent_view_count(listing.property_type, listing.district)   # over last 30 days
      + w_fav     * has_similar_favorite(listing)                                # 1 if user favourited a listing of same property_type+district
      + w_pref    * matches_explicit_prefs(listing)                              # 0/1 from NotificationPreferences filters
      + w_recency * 1 / max(age_in_days, 1)                                      # listing freshness
```

"Recent" = 30 days. Initial weights `w_view=0.4, w_fav=0.3, w_pref=0.2, w_recency=0.1`; tune from offline replay once we have a month of `VIEW` rows. Replace with a learned model in Phase 3 once volumes justify it.

## Decisions (formerly open questions)

- **Privacy.** The platform is Uzbekistan-only; per-user view history is sensitive but not GDPR-equivalent locally. Phase 1: collect without explicit opt-in but ship a "Forget my history" button in cabinet settings (read deletes from `ListingViewEvent` for that user_id). Phase 3: revisit if international expansion lands.
- **Notification ranking integration.** Out of scope for Phase 1 / 2. Reserve the door — `ListingViewEvent` schema is rich enough to support it later (e.g., suppress preferences-stage notifications for districts with zero `VIEW` rows in 30 days).
- **Anonymous views.** Don't collect under a session id in Phase 1. The cost (cookie + later attribution) outweighs the value while we're still small. Anonymous traffic still bumps `Listing.views_count` for the seller-dashboard view; only personalisation skips them.

## Acceptance criteria (Phase 1 piece only)

- `ListingViewEvent` table created via migration; indexes in place.
- `POST /listings/{id}/view` exists; accepts `{dwell_ms?}`; deduplicates per (user, listing, day) for `event_type=VIEW`.
- Frontend calls it on detail-page open (dwell unset) and on swipe-away (dwell = elapsed_ms).
- **Self-view guard** added — both `POST /listings/{id}/view` and the `views_count += 1` at `listings.py:1821` skip when `current_user.id == listing.seller.user_id`.
- Query "last 100 `VIEW` rows for user X" returns under 50 ms on the seeded index.
- Recommended feed unchanged — scoring lives in Phase 2.

## Path to DONE (Phase 1)

1. Schema: add `ListingViewEvent` migration with the columns + indexes above. Resolve naming with `../easy/seller-dashboard-counters.md` so both specs share the table.
2. Add `POST /listings/{id}/view` with dedup logic.
3. Add the self-view guard at both increment sites.
4. Wire frontend (detail open + swiper swipe-away).
5. Verify telemetry: rows accumulate, latency target met.

After (1)–(5), promote the data-collection scope to DONE. Phase 2 (scoring + recommended feed) stays under PARTIAL until the algorithm ships.
