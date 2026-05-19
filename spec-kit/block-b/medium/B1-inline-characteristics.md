# B1 — Inline characteristics block on the listing card

**Status:** NOT STARTED — chips for `rooms / area / floor` already render via the T-020 adapter; the four-pill characteristics block (year / condition / wall / key feature) is not built.
**Complexity:** MEDIUM — three card variants share an adapter; rendering is small but the data plumbing, the schema gap (no `year_built` column), and i18n+a11y per pill make it bigger than it looks.
**Block-B V2.0 ref:** B1.
**Why now:** without it, every parser-record card in the feed and Krutilka looks identical at a glance. Master-record cards (post-claim, with richer params from F1) finally get a way to surface their richer data.

## What's done

- **T-020 adapter** at `frontend/src/shared/ui/listing-card/adapter.ts:183-248` — canonical "card content" computation, no UI branching.
- **Card components** that consume the adapter:
  - `frontend/src/shared/ui/ListingCard.tsx:31-375` — feed grid card.
  - `frontend/src/shared/ui/MasonryListingCard.tsx:7-120+` — masonry layout.
  - `frontend/src/modules/buyer/feature/spinner/ui/ListingCard.tsx:25-254` — Krutilka full-screen card.
- **Existing chip strip** (rooms / area / floor / land_area) at `ListingCard.tsx:337-360`:

```tsx
{cardContent.chips.map((chip) => {
  const Icon = CHIP_ICON[chip.key] ?? IconRuler;
  return (
    <Box key={chip.key} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
      <Icon size={13} color="var(--mantine-color-gray-5)" stroke={2} />
      <Text size="xs" c="gray.6" fw={500}>{chip.label}</Text>
    </Box>
  );
})}
```

- **Krutilka slide content** at `ListingSlideContent.tsx:429-481` already renders Mantine Badges for `property_type / type / area / rooms / floor`.
- **Structured fields available on `Listing`** (`backend/app/db/models.py`):
  - `condition` (line 353) — string, nullable.
  - `wall_material` (line 433) — string, nullable.
  - `building_type` (line 350) — string, nullable.
  - `is_furnished` (line 372) — bool, nullable.
  - `amenities` (line 376) — `ARRAY(String)`.
  - `metro_station` (line 420) — string, nullable.
  - `halol_ok` (line 403) — bool, defaults present.

## What's missing

1. **The four-pill block itself.** No component renders a "characteristics" row separate from the existing chip strip. Spec wants it visually distinct from chips: chips are numeric base params; pills are categorical/boolean attributes.
2. **`year_built` (or equivalent) column does NOT exist** on `Listing`, `TelegramListing`, or `OLXListing`. `grep -nE "year_built|construction_year|year_of_construction"` in `backend/app/db/models.py` returns nothing. This is a hard gap — the spec explicitly lists "год дома" as the first pill. **Open question, see below.**
3. **Adapter doesn't expose pill-eligible fields.** Today `getCardContent()` returns chips for numeric base params only. It needs a parallel `pills` array selected from {condition, wall_material, building_type, is_furnished, amenities, metro_station, halol_ok}.
4. **Krutilka SlideContent** doesn't read pill-eligible fields either; it currently bundles them into the `Badge` row that already shows base params.
5. **i18n keys for pill labels.** Most pills want a translated category label, not the raw value. e.g. `condition="euro"` → "Евроремонт / Yevroremont / Еврoремонт". A6's i18n foundation exists; the keys need to be added.
6. **a11y per pill.** Each pill is a static text element today (no need for aria-label), but the screen-reader reading order matters when a card has both base chips and characteristic pills. Spec calls this out.
7. **F3 / SEO** — when SEO pages land, the same pill data should also flow into structured `schema.org` markup. Defer the wiring; document the contract here so the F3 implementation doesn't reinvent it.

## Path to DONE

### Step 0 — resolve the schema gap (before any code lands)

Pick one and proceed:

- **(a) Add `year_built` to `Listing` + source tables** via migration. Updates the LLM extractor (Block A's `llm_extractor.py`) to extract it. Coverage will be partial at first.
- **(b) Drop "year built" from B1's pills list** for now; rotate in `building_type` (kirpich/panel/monolit) as the second pill alongside `wall_material`. Spec deviation but functional immediately.
- **(c) Hybrid:** ship without `year_built` today (path b); track adding it as a follow-up after A7 metrics show what fraction of channels include the year in raw text.

This spec assumes **(c)**. If product chooses (a), add Step 0a as a migration.

### Step 1 — extend the adapter

`frontend/src/shared/ui/listing-card/adapter.ts` — add a `pills: PillItem[]` to the canonical card-content shape.

```ts
type PillKey = "condition" | "wall_material" | "building_type" | "key_feature";
type PillItem = { key: PillKey; label: string; ariaLabel: string };
```

Selection rules (in this priority order, max 4 emitted):
1. `condition` — if non-null and in known-set, label = `t(\`listing.condition.\${value}\`)`.
2. `wall_material` (apartments) **OR** `building_type` (apartments) — pick one to avoid duplication on apartments. If wall is set, prefer it; else fall back to building_type.
3. **Key feature** — first non-null match in this order: `halol_ok=true` → "Halol", `metro_station` non-null → `t("listing.nearMetro", { name: metro_station })`, `is_furnished=true` → "Furnished", first amenity in `amenities[]`.
4. **Year built** — only when Step 0 (a) is chosen.

Each pill gets an `ariaLabel` (per [B6](./B6-aria-labels-sweep.md)) — "Состояние: евроремонт", "Материал стен: кирпич", "Halol-ипотека".

### Step 2 — render the block

`frontend/src/shared/ui/ListingCard.tsx` — add a second strip under the existing chips strip, gated on `cardContent.pills.length > 0`. Same dense layout, no wrap to a second line. If pills overflow, truncate the last with ellipsis (don't drop entire pills).

### Step 3 — Krutilka slide

`frontend/src/modules/buyer/feature/spinner/ui/ListingCard.tsx` and `frontend/src/modules/buyer/pages/listing-detail/ui/main/ListingSlideContent.tsx:429-481` — replace the existing Badge clutter with the same pills (read from the same adapter shape).

### Step 4 — i18n keys

Add to all three locales (`ru/buyer.json`, `uz/buyer.json`, `uz-cyrl/buyer.json`):

- `listing.condition.{euro|good|fair|shell|turnkey|...}` — values must match what the parser extracts.
- `listing.wallMaterial.{brick|panel|monolith|wood}`.
- `listing.buildingType.{new_build|secondary|elite|...}`.
- `listing.nearMetro` — formatter string with `{{name}}`.
- `listing.halol` — short label.
- `listing.furnished` — short label.

### Step 5 — F3 contract

Document in this spec (and link from F3 when it starts): the `pills` array is the input the SEO page consumes for `schema.org/RealEstateListing` `additionalProperty`. F3 reads the same fields from the API; it does **not** re-run the selection logic.

## Behaviour & invariants

- **Pills come from structured fields only.** Never parse `ai_description_*` or `raw_text` to populate a pill. If `ai_description_ru` says "evроремонт" but `condition IS NULL`, the pill does NOT render. Recovery is via F2 (parser-confidence-driven re-parse), not by parsing AI text.
- **Pills hide entirely when zero.** No empty placeholder, no greyed-out "year unknown" skeleton.
- **Locale-aware truncation.** Uzbek strings are 20-40% longer than Russian; the strip must fit on a 360-px-wide phone without wrapping.
- **Order is stable.** Same listing shows pills in the same order every time (driven by the priority list in Step 1, not by field-iteration order).
- **a11y reading order** — base chips first, then pills. Pill `ariaLabel` always reads the category and the value: "Состояние: евроремонт", not just "евроремонт".

## Acceptance criteria

- A claimed-listing card with `condition="euro"`, `wall_material="brick"`, `halol_ok=true`, `metro_station="Чиланзар"` renders four pills in the documented order.
- A parser-record card with only `condition` set renders one pill; the rest of the strip is absent.
- A card where every pill-eligible field is null does NOT render the pill strip; layout collapses to the existing base-chips state.
- Krutilka full-screen slide shows the same pills, not the legacy verbose-Badge row.
- Switching locale (ru → uz → uz-cyrl) re-translates every pill label without remount glitches.
- Reading the card with VoiceOver / TalkBack lists the pills as "<category>: <value>".
- (Open) If `year_built` is added (Step 0a), the migration ships first; otherwise B1 ships without it.

## Edge cases

- **Pill text overflow** — when a Mantine `Pill` would push the row over the card width, truncate the *last* pill's text with `…`, never drop a pill or wrap a row.
- **`metro_station` longer than 12 chars** — abbreviate the prefix ("м. Чиланзар" → "м. Чил…") rather than the station name.
- **Listing in `GENERATION_FAILED` state (Block A status)** — pills still render; AI text doesn't gate them.
- **Master-record vs parser-record** — both render pills; parser records will have fewer pills on average until F2 increases confidence.
- **Saved-search compat** — saved searches don't reference card layout; safe.

## Production risks

- **Schema gap (year_built)** — if product picks Step 0(a), the migration is straightforward but we ship Block B partially without year coverage until the LLM extractor catches up.
- **Adapter regression** — extending T-020 adapter is the riskiest part; existing chips must not change. Snapshot tests on the adapter output recommended.
- **Krutilka slide layout** — replacing the badge clutter with pills changes vertical rhythm; coordinate with [B2](./B2-text-contrast-overlay.md) for the overlay height.

## Dependencies

- **Upstream:** A6 (i18n foundation, done), A7 (parser quality and `ai_description_*` columns, done — but pills do NOT consume AI fields; only structured params).
- **Downstream:** B2 (Krutilka slide layout — pills sit alongside the AI short description and price under the gradient), F3 (SEO `additionalProperty` consumes pill data).
- **Blocks nothing.**

## Open questions

1. **`year_built` column** — add now (Step 0a) or defer (Step 0c)? Recommendation: defer; Block A's parser metrics aren't measuring year-extraction success yet, so we don't know the coverage we'd advertise.
2. **`wall_material` vs `building_type`** — which to show for apartments when both are set? Spec lumps them. Recommendation: prefer `wall_material` (more specific); fall through to `building_type` only when wall is null.
3. **Pill size on small phones (320 px)** — strict no-wrap, or allow a second line for that breakpoint? Spec says no-wrap; verify with design.
4. **`amenities[]` ordering** — if multiple amenities, which one is the "key feature"? Use the first; document the deterministic rule.

## References

- `backend/app/db/models.py:350-433` — structured-field availability on `Listing`.
- `frontend/src/shared/ui/listing-card/adapter.ts:183-248` — adapter to extend.
- `frontend/src/shared/ui/ListingCard.tsx:337-360` — chip rendering site.
- `frontend/src/modules/buyer/feature/spinner/ui/ListingCard.tsx:25-254` — Krutilka card.
- `frontend/src/modules/buyer/pages/listing-detail/ui/main/ListingSlideContent.tsx:429-481` — slide badge row to replace.
- [B2](./B2-text-contrast-overlay.md), [B6](./B6-aria-labels-sweep.md), [A6](../../block-a/medium/A6-i18n-leaks.md), [A7](../../block-a/hard/A7-parser-f1-trigger.md).
