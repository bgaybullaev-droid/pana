# B6 — Aria-label sweep on icon-only buttons

**Status:** PARTIAL — worse than the spec's pessimistic baseline. Of 18 sampled icon-only buttons, **0 carry an `aria-label`**. There are 38 `ActionIcon` and 26 `UnstyledButton` instances in the buyer module alone.
**Complexity:** MEDIUM — the per-button change is trivial; the volume, the dynamic-state logic, and the i18n-key namespace work make it medium.
**Block-B V2.0 ref:** B6.
**Why now:** WCAG-A baseline; also stabilises automated tests by giving them a non-fragile selector.

## What's done

- **i18n foundation** is in place (A6 — `ru` / `uz` / `uz-cyrl` dictionaries, `formatNumber` helper, plural support).
- **Some buttons are inherently labelled** — the chip groups, deal-type tiles, and accordion-trigger types are buttons-with-text and don't need `aria-label`.
- **Telegram WebApp BackButton** (when used) is auto-labelled by the Telegram client.

## What's missing

The audit (sample of 18 representative buttons, see References for file:line each) found **zero** of the icon-only buttons carry an `aria-label`. Critical offenders:

| Where | File:line | Today | Needs |
|---|---|---|---|
| Home filter trigger (icon + count badge) | `home/Page.tsx:467` | no label | `t("aria.openFilters", { count })` |
| Home save-search heart | `home/Page.tsx:511-524` | no label, dynamic state | `t("aria.savedSearch.${state}")` |
| Home notification bell (with count) | `home/Page.tsx:532` | no label | `t("aria.notifications.${state}", { count })` |
| Home X-clear search | `home/Page.tsx:450` | no label | `t("aria.clearSearch")` |
| Card favorite heart | `ListingCard.tsx:240-255` | no label, dynamic | `t("aria.favorite.${isFav?'remove':'add'}")` |
| Slide like button | `ListingSlideContent.tsx:237` | no label | `t("aria.like")` |
| Slide message button | `ListingSlideContent.tsx:293` | no label | `t("aria.contactSeller")` |
| Slide map button | `ListingSlideContent.tsx:324` | no label | `t("aria.openMap")` |
| Seller listings menu (3-dots) | `seller/listings/Page.tsx:337` | no label | `t("aria.listingActions")` |
| Favorites X-clear | `favorites/Page.tsx:282` | no label | `t("aria.clearSearch")` |
| Saved-search delete | `SavedSearchCard.tsx` | no label | `t("aria.deleteSavedSearch")` |
| Custom back button (SearchInput) | `SearchInput.tsx:48` | no label, custom — not TG BackButton | `t("aria.back")` |

**Coverage today: 0 / 18 = 0%.** Spec target: 100% on interactive icon-only buttons.

There is **no existing convention** for the i18n namespace — no keys with the `aria.` prefix exist in any locale file (`grep "aria" frontend/src/shared/i18n/locales` returns nothing).

Decorative icons (e.g. the type-icon inside a card chip) generally lack `aria-hidden="true"`. Screen readers re-read every icon character.

## Path to DONE

### Step 1 — establish the i18n namespace

Add an `aria.*` namespace under each locale's `common.json` (the most cross-cutting namespace; aria labels appear on every page):

```json
// ru/common.json
{
  "aria.back": "Назад",
  "aria.clearSearch": "Очистить поиск",
  "aria.openFilters": "Открыть фильтры",
  "aria.openFilters_one": "Открыть фильтры, {{count}} активный",
  "aria.openFilters_few": "Открыть фильтры, {{count}} активных",
  "aria.openFilters_many": "Открыть фильтры, {{count}} активных",
  "aria.openFilters_other": "Открыть фильтры, {{count}} активных",
  "aria.notifications": "Уведомления",
  "aria.notifications_unread": "Уведомления, {{count}} новых",
  "aria.savedSearch.add": "Сохранить поиск",
  "aria.savedSearch.remove": "Убрать из сохранённых",
  "aria.favorite.add": "Добавить в избранное",
  "aria.favorite.remove": "Убрать из избранного",
  "aria.like": "Нравится",
  "aria.contactSeller": "Связаться с продавцом",
  "aria.openMap": "Открыть карту",
  "aria.listingActions": "Действия с объявлением",
  "aria.deleteSavedSearch": "Удалить сохранённый поиск",
  "aria.share": "Поделиться",
  "aria.addListing": "Добавить объявление"
}
```

Mirror in `uz/common.json` and `uz-cyrl/common.json` (~25 keys × 3 locales).

### Step 2 — sweep the buyer module

For each icon-only `ActionIcon` / `UnstyledButton`, add `aria-label={t("aria.…")}`. Where the label depends on state (heart, bell with count), use the dynamic key form:

```tsx
// Heart toggle
<ActionIcon
  aria-label={t(isFavorited ? "aria.favorite.remove" : "aria.favorite.add")}
  onClick={...}
>
  {isFavorited ? <IconHeartFilled/> : <IconHeart/>}
</ActionIcon>

// Bell with count
<ActionIcon
  aria-label={
    unreadCount > 0
      ? t("aria.notifications_unread", { count: unreadCount })
      : t("aria.notifications")
  }
>
  <IconBell/>
  {unreadCount > 0 && <Badge>{unreadCount}</Badge>}
</ActionIcon>
```

### Step 3 — sweep the seller and admin modules

The audit only sampled the buyer module. Repeat the same pass in `frontend/src/modules/seller/` and `frontend/src/modules/admin/`. The 3-dots menu, the eye/contact chips on cabinet cards, and the admin-source-page action icons (added in Block A's A8) all need labels.

### Step 4 — decorative icons

Add `aria-hidden="true"` to icons inside buttons-with-text and inside non-interactive card content (e.g. the property-type icon in a chip). Heuristic: if the icon is the *only* content of a clickable element, it needs a label; if it's purely decorative beside text, hide it from AT.

### Step 5 — context-disambiguating labels for repeated icons

If a page has five "Share" buttons (one per listing), each label includes the listing title:

```tsx
aria-label={t("aria.shareListing", { title: listing.title })}
```

Add `aria.shareListing` to the locale set with an interpolation slot.

### Step 6 — verification

- Run an a11y linter (e.g. `eslint-plugin-jsx-a11y` rule `jsx-a11y/no-noninteractive-element-interactions`) — report zero violations on the new code.
- Manual VoiceOver / TalkBack pass on the home page, listing detail, seller dashboard.

## Behaviour & invariants

- **Every interactive icon-only element has a localised `aria-label`.** Decorative icons have `aria-hidden="true"`.
- **Dynamic states update the label** — heart toggle, bell count, sort-active state.
- **Counters are spoken** — "Уведомления, 3 новых", not "Уведомления".
- **Repeated icons disambiguate** — share-on-listing-X says which listing.
- **All labels live in `common.json`** under the `aria.*` namespace (single source of truth across modules).
- **No hardcoded label strings** anywhere in TSX after this sweep.

## Acceptance criteria

- `grep -rE "<ActionIcon[^>]*>" frontend/src/modules` followed by inspection: every match either has `aria-label`, is wrapped in a button-with-text, or is followed by `aria-hidden="true"`.
- `grep -rE "<ActionIcon[^>]*aria-label=\"[А-Яа-я]" frontend/src` returns zero (no Russian hardcoded labels).
- `frontend/src/shared/i18n/locales/{ru,uz,uz-cyrl}/common.json` contain the full `aria.*` key set.
- VoiceOver test on iOS / TalkBack on Android: heart, bell, share, dots, back are all read with their action label.
- `eslint-plugin-jsx-a11y` passes on the touched files.

## Edge cases

- **Telegram WebApp BackButton (auto)** — when used, no label needed; the Telegram client handles it. Custom back arrows (e.g. `SearchInput.tsx:48`) DO need a label.
- **Tooltip + aria-label** — Mantine `Tooltip` already exposes its label to AT via `aria-describedby`. Don't double-up; if a tooltip is present, you can omit `aria-label` on the inner icon. (Confirm Mantine's behaviour for the version in use.)
- **Counter disagreement** — bell shows `99+` but reads as "Уведомления, 100 новых" (real number, not the visual cap). That's correct behaviour for screen readers; document.
- **Theme switch** — no aria-label changes when theme changes; labels are theme-agnostic.
- **Long uz labels** — labels are read sequentially by AT, not laid out visually, so length is not a concern.

## Production risks

- **Mass-edit churn** — touching ~50 buttons across 30+ files invites merge conflicts. Land in 2–3 PRs split by module: buyer, seller, admin.
- **Dynamic-state regressions** — easy to break the heart toggle's label by forgetting to flip the key on state change. Add a small test (RTL `screen.getByRole("button", { name: /Удалить/i })` after toggle).
- **Locale drift** — when adding new aria keys, all three locales must update or fallback shows English-ish keys. Keep the JSON files synced via the existing structure.

## Dependencies

- **Upstream:** A6 (i18n foundation — done).
- **Coupled:** B5 (new accordion controls and "Expand all" button need labels added to the same key set), B7 (action button inside `EmptyState` may inherit label from `actionLabel` text — already accessible).
- **Blocks:** none.

## Open questions

1. **Namespace location** — `common.json` (recommended) or per-module (`buyer.json`, `seller.json`)? Recommend `common.json` because aria-labels for shared UI (heart, share) appear in multiple modules.
2. **Plural-rule depth for counts** — Russian needs four forms; uz two. Use i18next's plural suffix convention. Already wired (A6).
3. **Should the sweep also assert WCAG AA contrast on focus rings?** Out of scope; that's WCAG AA, not A. Defer.

## References

- `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:450, 467, 511-524, 532` — top offenders.
- `frontend/src/shared/ui/ListingCard.tsx:240-255` — favorite heart on cards.
- `frontend/src/modules/buyer/pages/listing-detail/ui/main/ListingSlideContent.tsx:237, 293, 324` — slide actions.
- `frontend/src/modules/seller/pages/listings/ui/page/Page.tsx:337` — 3-dots menu.
- `frontend/src/modules/buyer/feature/spinner/ui/SearchInput.tsx:48` — custom back button.
- [A6](../../block-a/medium/A6-i18n-leaks.md), [B5](./B5-progressive-filter-disclosure.md), [B7](../easy/B7-empty-state-unification.md).
