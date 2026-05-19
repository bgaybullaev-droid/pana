# B7 — Unified `EmptyState` component

**Status:** PARTIAL — component exists and is used in three places; ~5 inline duplicates remain; `variant` prop is missing.
**Complexity:** EASY — small refactor + extending a single component's prop API.
**Block-B V2.0 ref:** B7.
**V1 cross-ref:** none direct.
**Why now:** lowest-priority item in Block B but it's the cheapest to ship and unblocks consistent visuals for B1/B2/B3 follow-up work that has its own empty branches.

## What's done

- **Component exists:** `frontend/src/shared/ui/EmptyState.tsx` (~57 lines). Current prop interface:

```tsx
interface EmptyStateProps {
  icon: FC<TablerIconsProps>;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}
```

- **Three live consumers (Block A landed two of them):**
  - `frontend/src/modules/seller/pages/found/ui/page/Page.tsx` — error-state and empty-state branches added by A3.
  - `frontend/src/modules/seller/pages/listings/ui/page/Page.tsx:484-499` — empty-listings case.

## What's missing

1. **No `variant` prop.** Spec wants `variant: "default" | "error" | "search-no-results"` so the same component can render the right icon/copy treatment per context.
2. **`action` not composed.** Today it's two flat props (`actionLabel`, `onAction`); spec wants one composite `{ label, onClick, variant }` to support styling the action button per context.
3. **Inline duplicates** still in the codebase:
   - `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:1257-1289` — filter-no-results state (icon + title + description + reset button), uses `IconSparkles`.
   - `frontend/src/modules/buyer/pages/favorites/ui/page/Page.tsx:370-395` — listings tab empty.
   - `frontend/src/modules/buyer/pages/favorites/ui/page/Page.tsx:420-441` — saved-searches tab empty.
   - `frontend/src/modules/buyer/pages/favorites/ui/page/Page.tsx:235-252` — unauthenticated empty.
   - `frontend/src/modules/buyer/pages/listing-detail/...` — 404 / not-found inline.
4. **No filter-no-results "Reset filters" pattern** as a first-class variant — the home page hand-rolls one.
5. **Prop API inconsistency** — when migrating inline duplicates, half of them want a primary action button, half want a secondary "go back" link. The current single `actionLabel/onAction` doesn't model that.

## Path to DONE

1. **Extend props (backward-compatible).** Keep `actionLabel`/`onAction` for backward compat, add `action?: { label, onClick, variant? }` and `variant?: "default" | "error" | "search-no-results"`. New consumers use `action`; old ones keep working until migrated.

```tsx
interface EmptyStateProps {
  icon: FC<TablerIconsProps>;
  title: string;
  description?: string;
  actionLabel?: string;          // legacy, deprecated
  onAction?: () => void;         // legacy, deprecated
  action?: { label: string; onClick: () => void; variant?: "filled" | "outline" };
  variant?: "default" | "error" | "search-no-results";
}
```

Variant treatment:
- `default` — current blue circle + sparkles tone.
- `error` — red icon background, action button color="red".
- `search-no-results` — gray icon background, primary action is "Reset filters".

2. **Migrate inline duplicates** — five sites listed above. Each becomes a single `<EmptyState ...>` call with appropriate `variant`. Delete inline JSX.

3. **Standardise the filter-no-results case** — home page uses the new `variant="search-no-results"`. The reset-filters callback is wired to `clearFilters` from the unified store (see [B3](../hard/B3-search-surface-unification.md)). If B3 hasn't landed yet, it can wire to whichever store the home page currently uses.

4. **i18n keys** — every `title` and `description` goes through the `t(...)` lookup. Most already do; verify the inline duplicates carry their keys forward instead of regressing to hardcoded strings.

5. **a11y** — the title becomes a heading inside the component (`role="status"` or `<h3>` depending on context). The action button has its label text — no aria-label needed unless icon-only. See [B6](../medium/B6-aria-labels-sweep.md) for the icon-button rules.

## Behaviour & invariants

- **Loading vs empty are distinct states.** The component never renders during `isLoading` — that's skeleton territory. The home/favorites screens already enforce this; preserve it during migration.
- **One source of truth** — when an inline duplicate is removed, no second sibling can re-implement an empty card without going through `EmptyState`.
- **Variant is purely visual.** Logic (whether to render, what action to wire) stays at the call site.
- **i18n** — no hardcoded strings inside the component or at any call site after migration.

## Acceptance criteria

- `frontend/src/shared/ui/EmptyState.tsx` accepts `variant` and `action` props in addition to the legacy two.
- Five identified inline duplicates are removed and replaced with `<EmptyState>` calls.
- The home page's filter-no-results state uses `variant="search-no-results"` with a reset-filters action.
- `grep -rE "(IconSparkles|IconHeart|IconSearch).*Stack.*Title.*Text" frontend/src/modules` returns zero results in pages that have a logical empty branch (modulo intentional non-empty-state usages).
- Every empty-state title and description goes through `t(...)`.

## Edge cases

- **Old vs new prop API at the same call site.** A consumer might pass both `actionLabel` (legacy) and `action` (new). The new prop wins; emit a `console.warn` once in dev mode.
- **Nested `action.variant` vs the surrounding `variant`.** `action.variant` is the button style; the outer `variant` is the icon/colour treatment. They don't conflict — document explicitly.
- **Listing-detail 404 — different context.** The 404 branch arguably wants `variant="error"`, not `default`. Confirm with product before flipping.
- **a11y reading order** — when `variant="search-no-results"` is used, the reset-filters action is the primary CTA; ensure it's the first focusable element after the title.

## Production risks

- **Visual drift during migration.** The five inline duplicates have slightly different dimensions, paddings, gradients. Before/after screenshots per migration step prevent regression.
- **Saved searches embed empty-state in a popover** — the `EmptyState` default vertical sizing might overflow. Add a `compact` size flag if needed (call out as "may add a `size` prop later" in the PR description).

## References

- `frontend/src/shared/ui/EmptyState.tsx` — component to extend.
- `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:1257-1289` — first migration target.
- `frontend/src/modules/buyer/pages/favorites/ui/page/Page.tsx:235-252, 370-395, 420-441` — three migration targets.
- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx` — already on EmptyState (template for migrations).
- [A3](../../block-a/easy/A3-mock-data-found.md) — Block-A precedent for empty/error/skeleton.
- [B6](../medium/B6-aria-labels-sweep.md) — a11y for the action button.
