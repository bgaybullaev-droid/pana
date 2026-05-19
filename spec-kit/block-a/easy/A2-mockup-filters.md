# A2 — Drop "Mockup" badges in B2C filters

**Status:** PARTIAL — three of the five badged sections are actually wired to the backend already; two truly have no filter; the badge is the wrong signal in both cases.
**Complexity:** EASY — drop badges where filters work; either implement two missing filters or hide those two cards.
**Block-A V2.0 ref:** A2 (Section "A2. Убрать Mockup-секции из B2C-фильтров").
**Why now:** A visible "Mockup" label on a public buyer screen is a stronger negative signal than any review.

## What's done

The buyer "preferences" page (the filter-equivalent on the buyer home) lives at `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx`. It renders five sections behind a `showMockup` flag map (`Page.tsx:591`) with a shared `MockupBadge` (line 599):

```tsx
const showMockup = {
    buildingType: true,
    houseType:    true,
    condition:    true,
    amenities:    true,
    utilities:    true,
};
const MockupBadge = <Badge color="gray" variant="light" size="xs">Mockup</Badge>;
```

The five PreferenceCard usages with `badge={MockupBadge}` are at lines **952, 968, 989, 1097, 1113**.

Backend filtering in `backend/app/api/v1/listings.py`:

| Field | Frontend badge | In `ListingFilters` schema | Filter applied in `/listings` |
|---|---|---|---|
| `building_type` | YES (mockup) | YES (`listings.py:159`) | **YES — `listings.py:816-817`** |
| `condition` | YES (mockup) | YES | **YES — `listings.py:818-819`** |
| `amenities` | YES (mockup) | YES | **YES — `listings.py:824-825`** |
| `house_type` | YES (mockup) | listed only as a dual-read mirror (`listings.py:181`) | **NO** |
| `house_condition` | YES (mockup) | dual-read mirror only (`listings.py:182`) | **NO** |
| `water_supply` | YES (mockup) | dual-read mirror only (`listings.py:184`) | **NO** |
| `utilities` | YES (mockup, shared with amenities at line 1107) | NO | **NO** |

So three filters are functional and silently mislabelled, and three to four are genuinely absent.

Saved searches **do exist** — `backend/app/api/v1/saved_searches.py` + `backend/app/services/saved_search_matcher.py` + `frontend/src/modules/buyer/feature/saved-searches/`. They serialize the filter object as JSON, so dropping a key from the schema must not break old payloads.

## What's missing

1. **`MockupBadge` is hardcoded on already-working filters.** `building_type`, `condition`, `amenities` need their `badge={MockupBadge}` prop removed.
2. **Three filters not enforced server-side.** `house_type`, `house_condition`, `water_supply` are in the model but not in `ListingFilters` and not applied in the `/listings` query.
3. **`utilities` has no model column at all** — it's a UI grouping inside the same card as `amenities` (`Page.tsx:1107-1139`). Either rename to a real backend field or fold its options under `amenities`.
4. **Saved-search forward-compat** — `saved_search_matcher.py` reads JSON filter dicts; if we add three new keys, old saved searches without them must still match.

## Path to DONE

The spec offers two paths. Recommend a **hybrid**:

### Hybrid (recommended)

1. **Drop badges on already-working filters** — set `showMockup.buildingType`, `showMockup.condition`, `showMockup.amenities` to `false` (or delete those keys and the `{showMockup.x && ...}` guards). Half-hour change.
2. **Hide `house_type`, `house_condition`, `water_supply` cards** until backend filtering ships (Path 2 from the spec). Drop the three sections from the JSX, leave the model columns intact for parser to keep populating. Add `// TODO(A2): re-enable when backend filter lands` next to the deleted blocks (one-line breadcrumb is fine; deeper docs aren't worth it).
3. **Fold `utilities` into `amenities`** — merge the option list, since amenities already supports an array filter at `listings.py:824-825`.

Total: ~half a day.

### Path 1 (full backend filtering)

1. Add `house_type`, `house_condition`, `water_supply` to `ListingFilters` Pydantic in `listings.py`.
2. Apply each in the query block around `listings.py:815-830`. Pattern matches the existing `building_type` filter exactly.
3. Drop all five `badge={MockupBadge}` props.
4. Backfill: parser already extracts these for new listings (see [A7 hard spec](../hard/A7-parser-f1-trigger.md)); old listings will return `NULL` and must not be silently filtered out — gate filter application on `is_not(None)`-aware logic per spec edge case ("if user didn't select a value, listings with NULL field still show").

Effort: ~1.5 days. Recommend hybrid unless A7 lands first and parser coverage is verified.

## Behaviour & invariants

- **Removing a filter key must not break saved searches.** `saved_search_matcher.py` ignores unknown keys silently — verify before deletion.
- **NULL-tolerant filtering** — applying a value-set filter must skip listings where the column is NULL (i.e. don't translate `field = ANY(values)` to also exclude NULL when the user just didn't tick anything).
- **No `Mockup` text anywhere in the production bundle** — `grep -r "Mockup" frontend/src --include="*.tsx"` returns zero hits.

## Acceptance criteria

- Zero `MockupBadge` JSX in `Page.tsx`.
- Zero "Mockup" text rendered in the buyer UI in any locale.
- Either: all five sections work end-to-end (Path 1), or the three unimplemented sections are deleted and a single-line `// TODO(A2)` marker remains where they were (hybrid).
- An old saved search containing `house_type` / `house_condition` / `water_supply` keys still loads without console error and still filters by the keys it does support.

## References

- `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:591-599` — `showMockup` map + badge definition.
- `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:952, 968, 989, 1097, 1113` — five PreferenceCard usages with `badge={MockupBadge}`.
- `backend/app/api/v1/listings.py:159, 181-184` — dual-read mirror fields.
- `backend/app/api/v1/listings.py:816-825` — current filter application block.
- `backend/app/api/v1/saved_searches.py` and `backend/app/services/saved_search_matcher.py` — saved-search consumers.
