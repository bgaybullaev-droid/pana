# B5 — Progressive filter disclosure

**Status:** NOT STARTED — drawer is a flat ~19-filter list; active-count badge logic exists at the drawer-icon level but not per section.
**Complexity:** MEDIUM — wrapping the filters in 5 `Mantine.Accordion` sections is small, but auto-expand on saved-search load, per-section count badges, and cross-locale label fitting bring it to medium.
**Block-B V2.0 ref:** B5.
**Why now:** the drawer is a vertical "wall" today; the 80% case (deal type + property + district + rooms + price) would benefit immediately, no schema work needed.

## What's done

- **Filter drawer rendering** lives inline in `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:641-1207` — the originally-separate `frontend/src/modules/buyer/feature/filter/ui/FilterPanel.tsx` is legacy and not the live consumer.
- **All ~19 filters** are mounted in a flat list of `<PreferenceCard>` components (12 cards, some host multiple controls):
  - Sorting (4 chips: recommended / newest / cheapest / expensive)
  - Price range (`RangeSlider`)
  - Region (chip group, dynamic from `getRegionKeys`)
  - District (conditional chip group, depends on region)
  - Deal type (`DealTypeGrid`)
  - Property type (`PropertyTypeGrid`)
  - Building type (chip group, conditional on property type)
  - Area range (`RangeSlider`)
  - Rooms (`Chip.Group`: studio / 1–5+)
  - Condition (chip group, conditional on property type)
  - Amenities (chip group)
- **Active-filter counter at the drawer-icon level** at `home/Page.tsx:287-309`:

```tsx
const activeFilterCount = [
  searchQuery,
  filters.type?.length,
  filters.property_type?.length,
  filters.region?.[0],
  filters.district?.[0],
  filters.rooms?.length,
  filters.price_min,
  filters.price_max,
  ...
].filter(Boolean).length;
```

  Used at lines 483-505 to render the small badge on the drawer-trigger icon.

- **Block-A2 outcome respected:** `house_type` and `utilities` are hidden today; the three working filters (`building_type`, `condition`, `amenities`) are shown without "Mockup" badges. See [A2](../../block-a/easy/A2-mockup-filters.md).

## What's missing

1. **No section grouping at all.** The drawer is a flat list. Spec wants 5 collapsible groups:
   - **Основные** (open by default): deal type, property type, region, rooms, price
   - **Параметры объекта** (collapsed): area, floor, year built (when added), condition, wall material
   - **Удобства и инфраструктура** (collapsed): amenities, metro, parking
   - **Финансы и условия** (collapsed): currency, halol/nasiya, deposit, min lease term
   - **Контент и свежесть** (collapsed): photo-only, posted-since, verified seller
2. **No per-section active-count badge.** Today only one global badge on the drawer trigger.
3. **No auto-expand on saved-search load.** Loading a saved search should expand the sections that contain its active filters.
4. **No "Expand all / Collapse all" link.**
5. **Not all filters in the spec exist yet** — the schema lacks `year_built` (see [B1](./B1-inline-characteristics.md)) and no UI for `verified_seller`, `posted_since`, `min_lease_term`, `deposit`. They're listed in the spec sections but absent today; Step 0 below decides whether to ship without them or add stubs.

## Path to DONE

### Step 0 — pick the section split for what we have

The spec lists 5 sections; some of the filters they reference don't exist yet. Recommended pragmatic split using only what's in code today:

- **Основные:** deal type, property type, region, district, rooms, price.
- **Параметры объекта:** area, floor, condition, building type / wall material.
- **Удобства и инфраструктура:** amenities (the existing `ARRAY` field), metro_station.
- **Финансы и условия:** currency (UZS / USD), halol_ok.
- **Контент и свежесть:** sort order (currently in flat list; move here), photo-only (`requires images`), date posted (if added).

Anything in the spec that doesn't have a backend field today is **out of scope for B5**; reopen when the field exists.

### Step 1 — wrap with `Mantine.Accordion`

`home/Page.tsx:641-1207` — wrap the existing `<PreferenceCard>` blocks in `<Accordion>` with `multiple` mode and `defaultValue={["main"]}`:

```tsx
<Accordion
  multiple
  value={openSections}
  onChange={setOpenSections}
  variant="contained"
>
  <Accordion.Item value="main">
    <Accordion.Control>
      {t("filters.section.main")}
      {sectionCounts.main > 0 && <Badge size="xs">{sectionCounts.main}</Badge>}
    </Accordion.Control>
    <Accordion.Panel>{/* existing main filters */}</Accordion.Panel>
  </Accordion.Item>
  {/* …object, amenities, finance, content sections… */}
</Accordion>
```

### Step 2 — per-section active-count

Compute `sectionCounts` as a map of `section → count` derived from the existing `activeFilterCount` calculation, split by which keys belong to which section:

```ts
const SECTION_KEYS = {
  main: ["type", "property_type", "region", "district", "rooms", "price_min", "price_max"],
  object: ["area_min", "area_max", "floor_min", "floor_max", "condition", "wall_material", "building_type"],
  amenities: ["amenities", "metro_station"],
  finance: ["currency", "halol_ok"],
  content: ["sort", "requires_images", "date_posted"],
} as const;

const sectionCounts = Object.fromEntries(
  Object.entries(SECTION_KEYS).map(([sec, keys]) => [
    sec,
    keys.filter(k => isActive(filters, k)).length,
  ])
) as Record<keyof typeof SECTION_KEYS, number>;
```

### Step 3 — auto-expand on active or on saved-search load

Initial value of `openSections`: `["main", ...sections where count > 0]`. Re-runs when the page mounts or when a saved search applies its payload.

```ts
useEffect(() => {
  const auto = Object.entries(sectionCounts)
    .filter(([_, n]) => n > 0)
    .map(([sec]) => sec);
  setOpenSections(prev => Array.from(new Set([...prev, "main", ...auto])));
}, [savedSearchAppliedAt /* or filters object identity */]);
```

### Step 4 — "Expand all / Collapse all"

Two small `UnstyledButton`s above the accordion. Each toggles `openSections` to all-keys / `["main"]` respectively.

### Step 5 — i18n keys (5 sections × 3 locales = 15 strings)

Add to `ru/buyer.json`, `uz/buyer.json`, `uz-cyrl/buyer.json`:

- `filters.section.main` / `.object` / `.amenities` / `.finance` / `.content`
- `filters.expandAll`, `filters.collapseAll`

### Step 6 — narrow-screen check

On 320–360-px phones, accordion headers must not wrap. Use `Mantine.Text size="sm"` and verify with the longest uz translations.

## Behaviour & invariants

- **Filters work strictly on structured params** (continued from B1). Accordion is purely a presentational change; the underlying filter store is untouched.
- **All existing filters remain mounted** — the accordion hides them visually but they're still in the DOM (Mantine `Accordion` does this by default; if performance suffers on old phones, switch to lazy mounting).
- **Section state is per-session** — collapsing a section does not persist between drawer opens or reloads. (Spec explicitly out of scope.)
- **Auto-expand priority** — sections with active filters always expand, in addition to the user's manual choices. The user can still collapse them manually after that.
- **Active-count badge** — shows on collapsed sections only (no badge when expanded; the controls are visible). Some sections show 0 → no badge.

## Acceptance criteria

- The drawer renders a 5-section accordion with the keys from Step 0.
- "Основные" is expanded by default; the rest are collapsed.
- A saved search containing `condition=euro` opens the drawer with both **Основные** AND **Параметры объекта** expanded.
- A user manually collapses **Основные**, applies a price filter, closes/reopens the drawer — **Основные** is auto-re-expanded because it now has an active filter.
- "Expand all" reveals every section; "Collapse all" leaves only **Основные** open.
- Active-count badge "Параметры объекта (3)" renders when 3 of its filters are set.
- All section labels are localised in ru / uz / uz-cyrl; uz labels do not wrap on 360-px width.
- Total filter count remains the same (no filter is removed or hidden by B5).

## Edge cases

- **Saved search with active filter in a hidden section** — auto-expand opens that section. (Step 3.)
- **All filters cleared** — reset all section states to default (only **Основные** open).
- **Region picked → district visible (conditional)** — keep the conditional render inside the same panel; collapsing the section hides both naturally.
- **Performance** — Mantine `Accordion` keeps panels in the DOM by default. For old phones (Android 8–9 era), measure FPS while applying a filter; switch to `chevronPosition="left"` and lazy-mount panels if jank shows up.
- **Drawer height** — collapsing sections shouldn't make the drawer suddenly short; keep the bottom CTA pinned.

## Production risks

- **Filter discoverability** — collapsing 80% of filters is a visibility regression for power users. Mitigated by **Параметры объекта (N)** counter and "Expand all". Watch the analytics: if filter-application rate drops post-B5, consider opening more sections by default.
- **Saved-search backwards compat** — saved searches store flat key/value JSON; the accordion change does NOT touch the data layer. Verified.
- **Layout drift** — accordion adds vertical padding; check the drawer's max-height on small phones doesn't cause double-scrollbars.

## Dependencies

- **Upstream:** A2 (mockup sections handled — done), B3 (filter store unification — preferred to land first; without it B5 still works against the home-page store, but a future B3 refactor will need to revisit).
- **Coupled:** B6 (the new accordion controls and Expand-all buttons need aria-labels).
- **Blocks:** none.

## Open questions

1. **Five-section split** — the spec's section names are confirmed; the per-filter assignment in Step 0 is judgement. Confirm with product before coding.
2. **Persistence between sessions** — spec says "out of scope for MVP". Confirm or revisit later.
3. **Sort order placement** — spec implies it goes in **Контент и свежесть**, but it's the most-used control. Recommend keeping it at the top of the drawer (above the accordion entirely) so it doesn't get buried.
4. **Verified-seller / date-posted / min-lease-term** — backend support? Defer if absent.

## References

- `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:641-1207, 287-309, 483-505` — drawer + active-count.
- `frontend/src/modules/buyer/pages/home/model/stores/index.ts` — filter store.
- `frontend/src/modules/buyer/feature/filter/ui/FilterPanel.tsx` — legacy file, **not** the active consumer (clarify in PR; possible cleanup target).
- [A2](../../block-a/easy/A2-mockup-filters.md), [B1](./B1-inline-characteristics.md), [B3](../hard/B3-search-surface-unification.md), [B6](./B6-aria-labels-sweep.md).
