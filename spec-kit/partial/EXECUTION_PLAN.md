# Partial — Execution Plan (implementation-ready)

Build sequence for everything in `partial/`. **Zero open questions** — every shared decision (event-table schema, phone canonicalisation, self-view guard, dwell lifecycle) is finalised below. Steps reference these decisions instead of re-deciding.

~4 weeks at 2-3 devs.

---

## 0. Reference design — the cross-cutting pieces

These three pieces are referenced by multiple steps. They are **defined once, not redesigned per step**.

### 0.1 Self-view guard helper

**Location:** new file `backend/app/services/listing_views.py`.

```python
# backend/app/services/listing_views.py
from typing import Optional
from app.db.models import Listing, User

def is_self_view(user: Optional[User], listing: Listing) -> bool:
    """True iff the listing belongs to the user — no view / contact / event
    should count for the listing's own seller.

    Crawled listings without a claimed seller (`seller_id IS NULL`) are
    never self-views: there's no owner to compare against, so the call
    returns False even for an authenticated user.
    """
    if user is None or listing.seller_id is None:
        return False
    if listing.seller is None:  # eager-load not done — be defensive
        return False
    return listing.seller.user_id == user.id
```

**Reuse rule:** every increment / event-write site **must** call `is_self_view` first. Three sites today:
- `backend/app/api/v1/listings.py:~1821` — `resolve_listing()` `views_count` bump.
- `backend/app/api/v1/listings.py:NEW` — `POST /listings/{id}/view` (Step 6).
- `backend/app/api/v1/listings.py:NEW` — `POST /listings/{id}/contact` (Step 5).

If a future site bumps a listing-related counter, it must call this helper. No exceptions.

### 0.2 `ListingViewEvent` schema (event log for personalisation)

**Final schema** — Alembic migration `prx_listing_view_event`:

```sql
CREATE TABLE listing_view_event (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,  -- nullable
    listing_id  UUID NOT NULL,                                -- no FK; cross-source listings
    event_type  VARCHAR(16) NOT NULL,                         -- 'view' | 'contact' | 'share'
    viewed_at   TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    dwell_ms    BIGINT                                        -- nullable; meaningful only for 'view'
);

-- Read path: "last N events for user X"
CREATE INDEX idx_listing_view_event_user_time
    ON listing_view_event (user_id, viewed_at DESC)
    WHERE user_id IS NOT NULL;

-- Read path: "events for listing X by type"
CREATE INDEX idx_listing_view_event_listing_type_time
    ON listing_view_event (listing_id, event_type, viewed_at DESC);

-- Dedup: at most one row per (user, listing, type, calendar-day)
CREATE UNIQUE INDEX uq_listing_view_event_dedup
    ON listing_view_event (user_id, listing_id, event_type, (date(viewed_at)))
    WHERE user_id IS NOT NULL;
```

**Population rule — exact:**

| Path | Anonymous user (`current_user IS NULL`) | Authenticated non-self | Authenticated self-view |
|---|---|---|---|
| Detail open (`GET /listings/{id}`) | bump `Listing.views_count` only — no event row | bump `Listing.views_count` + insert `event_type='view'` row | skip everything (self-view guard) |
| Explicit view ping (`POST /listings/{id}/view`) | rejected with 401 (auth required) | upsert `event_type='view'` with dwell — see dedup below | skip everything |
| Contact reveal (`POST /listings/{id}/contact`) | rejected with 401 | bump `Listing.contacts_count` + insert `event_type='contact'` (if not already today) | skip everything |
| Share (future) | n/a | insert `event_type='share'` | skip everything |

**Dedup mechanic — exact SQL:**

```sql
INSERT INTO listing_view_event (user_id, listing_id, event_type, viewed_at, dwell_ms)
VALUES (:user_id, :listing_id, :event_type, now(), :dwell_ms)
ON CONFLICT (user_id, listing_id, event_type, (date(viewed_at))) WHERE user_id IS NOT NULL
DO UPDATE
   SET dwell_ms = GREATEST(
                    COALESCE(listing_view_event.dwell_ms, 0),
                    COALESCE(EXCLUDED.dwell_ms, 0)
                  ),
       viewed_at = listing_view_event.viewed_at;  -- keep first-event-of-day timestamp
```

The partial unique index covers only `user_id IS NOT NULL`, so anonymous rows would never reach the conflict (and we don't write anonymous rows anyway).

**Single source of truth:**

- **Dashboard reads counters** (`Listing.views_count`, `Listing.contacts_count`, `COUNT(*) FROM favorites`). Counters are the canonical aggregate cache.
- **Personalisation reads events** (`listing_view_event WHERE event_type='view'`). The event table is the canonical history.
- The two are populated together in the same DB transaction; a failure in either rolls back both. Never read from one to compute the other.

### 0.3 Phone canonicalisation

**Function** — new helper at `backend/app/utils/phone.py`:

```python
import re

def canonicalize_phone(raw: Optional[str]) -> Optional[str]:
    """Canonical E.164 form for Uzbekistan numbers, or None if not parseable.

    Rules:
    - Strip every non-digit character.
    - 9 digits  → assume UZ subscriber, return '+998' + digits.
    - 12 digits starting with '998' → return '+' + digits.
    - Anything else → None (caller decides: reject or store NULL).
    """
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 9:
        return f"+998{digits}"
    if len(digits) == 12 and digits.startswith("998"):
        return f"+{digits}"
    return None
```

The existing `normalize_phone` (last-9-digits suffix) stays — used for the OTP / claim suffix-match query, **not** for storage. Storage uses `canonicalize_phone`.

---

## 1. Execution order

### Step 1 — Self-view guard wired at the existing site

**Feature:** `seller-dashboard-counters` (slice 1)
**Why first:** Every later step that bumps a counter or writes an event needs the helper. Land it now so nothing else has to remember.

**Patch:**
1. Create `backend/app/services/listing_views.py` with `is_self_view` (see §0.1).
2. In `backend/app/api/v1/listings.py` near the existing increment (~line 1821), import the helper and wrap the bump:
   ```python
   from app.services.listing_views import is_self_view
   ...
   if main_listing and not is_self_view(current_user, main_listing):
       main_listing.views_count = (main_listing.views_count or 0) + 1
       await db.commit()
       await db.refresh(main_listing)
   ```
3. Tests: (a) anonymous detail-open bumps; (b) other-user detail-open bumps; (c) seller's own detail-open does NOT bump; (d) crawled listing with `seller_id IS NULL` always bumps.

**Effort:** ½ day. **Touches:** `services/listing_views.py` (new), `api/v1/listings.py` (~5 lines).

### Step 2 — F108 master-record ranking + dedup

**Feature:** `partial/easy/F108-master-record-ranking`
**Why here:** Independent of all other partial work. Two-line edit; runs in parallel with Step 3.

**Patch in `backend/app/api/v1/listings.py:1186-1188` (Postgres feed path only — Meili path preserves Meili's relevance order and is intentionally not changed):**

```python
query = select(Listing).where(
    Listing.status == ListingStatus.ACTIVE,
    Listing.moderation_status == ModerationStatus.APPROVED,
    Listing.deleted_at.is_(None),
    Listing.master_record_id.is_(None),  # <-- 1: dedup filter
)
...
sort_column = getattr(Listing, filters.sort_by)
order_clauses = [
    Listing.is_boosted.desc(),
    (Listing.claimed_at.is_not(None)).desc(),  # <-- 2: claim boost
    sort_column.desc() if filters.sort_order == "desc" else sort_column.asc(),
]
query = query.order_by(*order_clauses)
```

**Acceptance:** existing tests pass; manual checks — claimed > unclaimed at same age, paid > claimed, duplicate parsed rows hidden.

**Effort:** ½ day. **Touches:** `api/v1/listings.py` (3 lines).

### Step 3 — F089 phone uniqueness helper + backfill (auth-track parallel)

**Feature:** `partial/easy/F089-phone-uniqueness`
**Why here:** Independent of the listings track. Different file (`auth.py`); different reviewer; runs on a separate dev.

**Patch list:**

1. **Add `canonicalize_phone`** to `backend/app/utils/phone.py` (see §0.3).
2. **Add `reserve_phone_for_user`** helper to `backend/app/services/account_linking.py`:
   ```python
   async def reserve_phone_for_user(
       db: AsyncSession,
       *,
       incoming_phone: str,           # already canonicalised by caller
       target_user_id: Optional[UUID],
   ) -> None:
       """Hard-stop on active clash; free stale users.phone + sellers.phone.
       Call before db.commit() in every login flow that sets User.phone."""
       # Active clash → 400
       q = select(User).where(
           User.phone == incoming_phone,
           User.deleted_at.is_(None),
       )
       if target_user_id:
           q = q.where(User.id != target_user_id)
       if (await db.execute(q)).scalar_one_or_none():
           raise BadRequestException("This phone is linked to another account.")

       # Free soft-deleted users.phone
       stale_q = select(User).where(
           User.phone == incoming_phone,
           User.deleted_at.is_not(None),
       )
       if target_user_id:
           stale_q = stale_q.where(User.id != target_user_id)
       for stale in (await db.execute(stale_q)).scalars().all():
           stale.phone = None

       # Free sellers.phone owned by anyone other than the target user
       seller_q = select(Seller).where(Seller.phone == incoming_phone)
       if target_user_id:
           seller_q = seller_q.where(Seller.user_id != target_user_id)
       for s in (await db.execute(seller_q)).scalars().all():
           s.phone = None

       await db.flush()
   ```
3. **Refactor `/auth/telegram`** to call this helper instead of inlining the logic (no behaviour change — verifies the helper).
4. **Add the call** before `db.commit()` in:
   - `login_buyer_phone` (`auth.py:~1074`),
   - `login_olx_phone` (`auth.py:~622`),
   - `login_telegram_channel` (`auth.py:~698`),
   - `verify_seller_otp` (`auth.py:~934`).

   In each, canonicalise the input first: `phone = canonicalize_phone(raw); if phone is None: raise BadRequestException(...)`. Then `await reserve_phone_for_user(db, incoming_phone=phone, target_user_id=user.id if user else None)`.

5. **Backfill migration** `prx_canonicalize_phone_format` (Alembic, runs once):

   ```python
   """Canonicalize users.phone and sellers.phone to E.164.

   Resolves duplicates by keeping the row with the most recent
   last_login_at (users) / updated_at (sellers); other rows lose their
   phone (NULL) so the unique index stays valid.

   Revision ID: prx_canonicalize_phone_format
   """
   from alembic import op
   import re

   def _canon(raw):
       if not raw: return None
       d = re.sub(r"\D", "", raw)
       if len(d) == 9: return f"+998{d}"
       if len(d) == 12 and d.startswith("998"): return f"+{d}"
       return None

   def upgrade():
       conn = op.get_bind()
       _canonicalize_table(conn, "users", "last_login_at")
       _canonicalize_table(conn, "sellers", "updated_at")

   def _canonicalize_table(conn, table, freshness_col):
       rows = conn.execute(
           f"SELECT id, phone, {freshness_col} FROM {table} WHERE phone IS NOT NULL"
       ).fetchall()
       groups = {}                  # canon -> list[(id, freshness)]
       invalid = []
       for r in rows:
           c = _canon(r.phone)
           if c is None:
               invalid.append(r.id)
           else:
               groups.setdefault(c, []).append((r.id, r[freshness_col]))
       winners = []                 # list[(id, canon)]
       losers = []                  # list[id]
       for canon, members in groups.items():
           members.sort(key=lambda m: m[1] or "1970-01-01", reverse=True)
           winners.append((members[0][0], canon))
           losers.extend(m[0] for m in members[1:])
       if invalid + losers:
           conn.execute(
               f"UPDATE {table} SET phone = NULL WHERE id = ANY(%s::uuid[])",
               (invalid + losers,),
           )
       for id_, canon in winners:
           conn.execute(
               f"UPDATE {table} SET phone = %s WHERE id = %s",
               (canon, id_),
           )

   def downgrade():
       # Original raw formats are unrecoverable post-canonicalisation.
       # Documented as no-op; restore from backup if rollback truly needed.
       pass
   ```

6. **Tests** for `reserve_phone_for_user` — four cases: free phone success / active-other clash → 400 / soft-deleted-user clash frees / seller-row clash frees. Plus one migration test on a seeded fixture.

**Effort:** ~2 days. **Touches:** `utils/phone.py`, `services/account_linking.py`, `api/v1/auth.py` (5 endpoints), 1 Alembic migration.

### Step 4 — `ListingViewEvent` migration (shared dependency)

**Feature:** shared between `seller-dashboard-counters` and `F077-personalization`.
**Why here:** Steps 5 and 6 both need this table. Land the migration alone, no consumers yet.

**Patch:** ship the Alembic migration in §0.2 verbatim. Add a `ListingViewEvent` SQLAlchemy model in `backend/app/db/models.py` with the same shape; export from `app.db`. No router work.

**Acceptance:** migration `alembic upgrade head` succeeds; `INSERT … ON CONFLICT … DO UPDATE` from §0.2 succeeds against an empty table; `EXPLAIN` confirms the index plan for the two read queries.

**Effort:** ½ day. **Touches:** 1 Alembic migration, `db/models.py` (~30 lines).

### Step 5 — Contact event endpoint + per-card chips

**Feature:** `seller-dashboard-counters` (slice 2)
**Why here:** Depends on Steps 1, 4. Single transaction writes both the counter and the event row.

**Patch:**

1. **`POST /listings/{id}/contact`** in `backend/app/api/v1/listings.py`:
   ```python
   @router.post("/{listing_id}/contact", status_code=204)
   async def record_contact(
       listing_id: UUID,
       current_user: User = Depends(get_current_user),  # auth required
       db: AsyncSession = Depends(get_db),
   ):
       listing = await db.get(Listing, listing_id, options=[selectinload(Listing.seller)])
       if listing is None:
           raise NotFoundException("Listing", str(listing_id))
       if is_self_view(current_user, listing):
           return  # silently no-op for the seller's own listing

       # Insert event with daily dedup; if dedup hits, no counter bump
       result = await db.execute(text("""
         INSERT INTO listing_view_event (user_id, listing_id, event_type, viewed_at)
         VALUES (:uid, :lid, 'contact', now())
         ON CONFLICT (user_id, listing_id, event_type, (date(viewed_at)))
           WHERE user_id IS NOT NULL
         DO NOTHING
         RETURNING id
       """), {"uid": current_user.id, "lid": listing_id})
       inserted = result.scalar_one_or_none()
       if inserted is not None:
           listing.contacts_count = (listing.contacts_count or 0) + 1
       await db.commit()
   ```

2. **Frontend wiring**: `frontend/src/shared/ui/ListingCard.tsx` — the «Связаться» button calls `apiClient.post(/listings/{id}/contact)` **before** revealing the phone. On non-204 errors, still reveal (don't block UX on telemetry failure).

3. **Favorites count chip on the seller card.** Extend the seller-listings query in `backend/app/api/v1/sellers.py` (the route that backs the seller portfolio) with a correlated subquery:
   ```sql
   (SELECT COUNT(*) FROM favorites WHERE listing_id = listings.id) AS favorites_count
   ```
   Add `favorites_count` to the response schema. Render a third chip in `seller/pages/listings/Page.tsx` next to views + contacts.

**Acceptance:** double-tap the contact button on the same day → `contacts_count` increments once; auth-required (anon → 401); self-tap is no-op (no event, no counter).

**Effort:** ~1 day. **Touches:** `api/v1/listings.py` (~30 lines), `api/v1/sellers.py` (subquery), `ListingCard.tsx` (~10 lines), `seller/pages/listings/Page.tsx` (~10 lines).

### Step 6 — F077 Phase 1: view event endpoint + dwell capture

**Feature:** `partial/hard/F077-personalization` (Phase 1 only — scoring deferred).
**Why here:** Depends on Steps 1, 4. Same table as Step 5; different `event_type`.

**Backend:**

```python
# backend/app/api/v1/listings.py
class RecordViewIn(BaseModel):
    dwell_ms: int | None = Field(default=None, ge=0, le=86_400_000)  # cap at 1 day

@router.post("/{listing_id}/view", status_code=204)
async def record_view(
    listing_id: UUID,
    body: RecordViewIn,
    current_user: User = Depends(get_current_user),  # 401 for anonymous
    db: AsyncSession = Depends(get_db),
):
    listing = await db.get(Listing, listing_id, options=[selectinload(Listing.seller)])
    if listing is None:
        raise NotFoundException("Listing", str(listing_id))
    if is_self_view(current_user, listing):
        return
    await db.execute(text("""
      INSERT INTO listing_view_event (user_id, listing_id, event_type, viewed_at, dwell_ms)
      VALUES (:uid, :lid, 'view', now(), :dwell)
      ON CONFLICT (user_id, listing_id, event_type, (date(viewed_at)))
        WHERE user_id IS NOT NULL
      DO UPDATE
        SET dwell_ms = GREATEST(
                         COALESCE(listing_view_event.dwell_ms, 0),
                         COALESCE(EXCLUDED.dwell_ms, 0)
                       )
    """), {"uid": current_user.id, "lid": listing_id, "dwell": body.dwell_ms})
    await db.commit()
```

The existing `views_count` increment in `resolve_listing()` (already protected by Step 1's guard) stays untouched — the counter and the event row are written by different code paths but cover the same population for authenticated non-self users.

**Frontend lifecycle — exact:**

`frontend/src/shared/lib/viewTracking.ts` (new):

```ts
export function trackView(listingId: string, isAuthenticated: boolean) {
  if (!isAuthenticated) return () => {};   // anonymous — skip
  const startedAt = performance.now();

  // Fire on mount with no dwell
  void apiClient.post(`/listings/${listingId}/view`, { dwell_ms: null }).catch(() => {});

  let sent = false;
  const fireDwell = () => {
    if (sent) return;
    sent = true;
    const dwell_ms = Math.round(performance.now() - startedAt);
    const url = `${apiClient.defaults.baseURL}/listings/${listingId}/view`;
    const body = JSON.stringify({ dwell_ms });
    // Prefer sendBeacon for unmount-during-close; fall back to keepalive fetch.
    if (navigator.sendBeacon?.(url, new Blob([body], { type: "application/json" }))) {
      return;
    }
    void fetch(url, {
      method: "POST", body, keepalive: true,
      headers: { "Content-Type": "application/json" },
      credentials: "include",
    }).catch(() => {});
  };

  const onVis = () => { if (document.visibilityState === "hidden") fireDwell(); };
  document.addEventListener("visibilitychange", onVis);
  window.addEventListener("pagehide", fireDwell);

  // Returned cleanup — call from React `useEffect` cleanup or Swiper `slideChange`.
  return () => {
    document.removeEventListener("visibilitychange", onVis);
    window.removeEventListener("pagehide", fireDwell);
    fireDwell();
  };
}
```

**Wiring sites — exact:**

- **Listing-detail page** (`frontend/src/modules/buyer/pages/listing-detail/ui/page/Page.tsx`):
  ```ts
  useEffect(() => trackView(listingId, isAuthenticated), [listingId, isAuthenticated]);
  ```
- **Krutilka swiper** (`frontend/src/modules/buyer/pages/home/ui/page/Page.tsx`):
  Per-slide bookkeeping:
  ```ts
  const cleanupRef = useRef<(() => void) | null>(null);
  // Swiper handler:
  onSlideChangeTransitionStart={(swiper) => {
    cleanupRef.current?.();
    const id = listings[swiper.activeIndex]?.id;
    if (id) cleanupRef.current = trackView(id, isAuthenticated);
  }}
  ```

**Failure mode:** all `POST /view` calls are fire-and-forget; the `.catch(() => {})` swallows errors (network, 4xx, 5xx). Personalisation tolerates missing data.

**Acceptance:**
- After 1 dev day of swipe-around, the table has rows; `EXPLAIN` of `SELECT * FROM listing_view_event WHERE user_id = ? ORDER BY viewed_at DESC LIMIT 100` shows index scan, runtime under 50 ms on the seeded dataset.
- Closing a tab on a detail page produces an event row with `dwell_ms > 0`.
- Anonymous user opens a listing → no row written.
- Seller opens own listing → no row written.

**Effort:** ~2-3 days. **Touches:** `api/v1/listings.py` (~25 lines), `shared/lib/viewTracking.ts` (new), 2 frontend pages (~5 lines each).

### Step 7 — Aggregate seller dashboard

**Feature:** `seller-dashboard-counters` (slice 3).
**Why here:** Depends on Step 5 (counters bumped reliably) and benefits from Step 6 (events accumulating, even though dashboard reads counters).

**Patch:**

1. **`GET /sellers/me/dashboard`** in `backend/app/api/v1/sellers.py`:
   ```python
   @router.get("/me/dashboard")
   async def my_dashboard(
       seller: Seller = Depends(get_current_seller),
       db: AsyncSession = Depends(get_db),
   ):
       agg = await db.execute(select(
           func.coalesce(func.sum(Listing.views_count),    0).label("total_views"),
           func.coalesce(func.sum(Listing.contacts_count), 0).label("total_contacts"),
       ).where(Listing.seller_id == seller.id, Listing.deleted_at.is_(None)))
       row = agg.one()

       fav_total = (await db.execute(
           select(func.count())
           .select_from(Favorite)
           .join(Listing, Favorite.listing_id == Listing.id)
           .where(Listing.seller_id == seller.id)
       )).scalar_one()

       top = (await db.execute(
           select(Listing.id, Listing.title_ru, Listing.views_count)
           .where(Listing.seller_id == seller.id, Listing.deleted_at.is_(None))
           .order_by(Listing.views_count.desc().nullslast())
           .limit(3)
       )).all()

       return {
           "total_views":     row.total_views,
           "total_contacts":  row.total_contacts,
           "total_favorites": fav_total,
           "top_listings":    [{"id": str(l.id), "title": l.title_ru, "views": l.views_count} for l in top],
       }
   ```

2. **UI band** at the top of `frontend/src/modules/seller/pages/listings/ui/page/Page.tsx` — three big numbers + a "top listings" preview.

**Acceptance:** numbers in the band match the sum of the per-card chips.

**Effort:** ~1 day.

### Step 8 — Pre-launch fixes (parallel batch)

**Feature:** `partial/medium/pre-launch-fixes` — items 2, 5, 6, 8.
**Why here:** Independent of every other partial spec. Run alongside steps 4-7.

8.5 — **`/search` redirect.** Add to `frontend/src/app/router/Router.tsx`:
```tsx
{ path: "/search", element: <Navigate to={`/?${new URLSearchParams(searchToFilter()).toString()}`} replace /> },
```
Delete the legacy `modules/buyer/pages/search/` module after one deploy cycle.

8.2 — **Mockup-filter feature flag.** In `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx`, gate the 5 mockup sections:
```tsx
const SHOW_MOCKUP = import.meta.env.VITE_SHOW_MOCKUP_FILTERS === "true";
{SHOW_MOCKUP && <MockupFilterSection ... />}
```
Default false in production `.env`. Wire each section to a real backend filter as backend lands.

8.6 — **i18n sweep.** Acceptance: `rg --type tsx '[А-Яа-я]' frontend/src/modules/seller | grep -v __tests__ | grep -v 'mockData' | grep -v '// '` returns 0 hits. Move every match to `shared/i18n/locales/{ru,uz}/seller.json`. UZ translations land in the same PR as RU.

8.8 — **Overlay contrast.** Out of scope of this plan as written — needs a designer to specify a solid-pill component (background colour, padding, padding-top relative to image) before a frontend dev can pick it up. Open a separate Figma + design ticket; remove from this plan once that ticket is filed.

**Effort:** Items 8.5, 8.2 — half a day each. Item 8.6 — 3-5 days (the dominant chunk). Item 8.8 — externalised.

### Step 9 — F077 Phase 2 scoring (deferred)

Don't start before ~30 days of `listing_view_event` rows have accumulated post-Step 6. Then implement linear scoring (`w_view·recent_view_count + w_fav·has_similar_favorite + w_pref·matches_explicit_prefs + w_recency/age_days`) with initial weights 0.4 / 0.3 / 0.2 / 0.1. Tune from offline replay. Out of scope for the present plan.

---

## 2. Dependency map

```
canonicalize_phone (§0.3) ──┐
reserve_phone_for_user      ├──► F089 (Step 3) — auth track
backfill migration          ┘

is_self_view (§0.1) ──┬──► Step 1 (existing site)
                      ├──► Step 5 contact endpoint
                      └──► Step 6 view endpoint

ListingViewEvent table (§0.2) ──┬──► Step 5 contact endpoint (event_type='contact')
                                └──► Step 6 view endpoint   (event_type='view')

Counters (Listing.{views,contacts}_count) ──► Step 7 dashboard read path

F108 ranking (Step 2) ─────────► (independent)
Pre-launch fixes (Step 8)  ────► (independent; Item 8.8 externalised)
```

The only cross-step shared write surface is `ListingViewEvent`; the dual-write rule from §0.2 is the contract.

---

## 3. Parallel work opportunities

### Two-dev team

| Week | Dev A (backend) | Dev B (frontend / mixed) |
|---|---|---|
| 1 | Step 1 guard → Step 4 migration → start Step 3 F089 | Step 2 F108 → Step 8.5 redirect → Step 8.2 mockup flag |
| 2 | Step 3 finish (helper, 4 callsites, backfill) → Step 5 backend | Step 5 frontend wiring → Step 8.8 design ticket open + handoff |
| 3 | Step 6 backend → Step 7 backend | Step 6 frontend (`viewTracking.ts` + 2 page wirings) |
| 4 | (review / buffer) | Step 7 UI band → Step 8.6 i18n sweep |

### Three-dev team

| Week | Dev A (listings) | Dev B (auth) | Dev C (frontend) |
|---|---|---|---|
| 1 | Steps 1, 2, 4 | Step 3 (helper + backfill) | Step 8.5, 8.2, 8.8 ticket-open |
| 2 | Step 5 backend | parallel review + tests | Step 5 frontend + start 8.6 i18n |
| 3 | Step 6 backend | (joins Dev C) | Step 6 frontend + 8.6 cont. |
| 4 | Step 7 backend | Phase-2 scoring prep | Step 7 UI + 8.6 finish |

**Hard "do not parallelise":**
- Steps 1 and 2 both edit `listings.py` near each other — Step 1 ships first; Step 2 rebases on top.
- Step 4 must be merged before any Step-5 or Step-6 PR opens (the consumers reference the table).
- Step 3's backfill migration must run before the new `reserve_phone_for_user` callsites deploy (otherwise existing rows trip the unique index).

**Safe to parallelise on day 1:**
F089 (auth.py) ⫽ F108 (listings.py order_by) ⫽ Step 8 frontend polish — three different files, three different reviewers.

---

## 4. Done definition

A feature exits `partial/` when:

1. Every "Missing" item in its spec is checked off and acceptance criteria pass.
2. The PR that ships the last commit also **moves the spec file** to `done/<complexity>/` and rewrites it to describe the new reality (no "what's missing" section). Same diff, not a follow-up.
3. The PR updates inbound links: `spec-kit/README.md` and any spec referencing the old path.
4. Reviewer checks (1)-(3) before merging.

`F077-personalization` ships in two halves. **Step 6 does NOT promote** the spec to `done/`; promotion waits for Step 9. Until then the spec stays in `partial/hard/` with the Phase-1 portion marked complete inline.
