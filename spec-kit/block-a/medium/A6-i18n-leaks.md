# A6 — Russian hardcode → i18n sweep

**Status:** PARTIAL — `uz` and `ru` dictionaries are healthy and recently extended; `uz-latn` JSON files do not exist; several Cyrillic strings still live in `.tsx`.
**Complexity:** MEDIUM — bounded sweep across known offenders, but it includes adding a third locale set, ICU plurals, and a regex/data audit.
**Block-A V2.0 ref:** A6 (Section "A6. Утечки русского хардкода в i18n", Ф-14).
**Why now:** Block A V2.0 introduces a wave of new UI (claim/reject buttons, push notifications, AI disclaimer, view counters). Adding the strings now while writing them is cheap; bolting them on later doubles the cost.

## What's done

- **Two locales present** — `frontend/src/shared/i18n/locales/{ru,uz}/{admin,buyer,seller,common}.json`. `uz/seller.json` and `ru/seller.json` are at parity (~443 quoted entries each).
- **Recent additions** in commit `fc3d793` to `uz/seller.json` (and presumed `ru/`): `createListing.urgentFlag`, `cityLabel`, `jkNameLabel`, `metroStationLabel`, `marketTypeLabel`, `wallMaterialLabel`, `furnitureLabel`, 7 commercial-type variants, 4 land-purpose variants, 4 condition variants, plus `validation.cityRequired`, `validation.commercialTypeRequired`. ~90 new keys.
- **Backend does not leak Russian.** `grep -nE 'detail="[А-Яа-я]' backend/app` returns nothing — `HTTPException` payloads are codes that the frontend translates, which is the spec-correct architecture.

## What's missing

1. **`uz-latn` (Latin-script Uzbek) directory does not exist.** `frontend/src/shared/i18n/locales/` contains only `ru/` and `uz/`. The codebase references `uz-latn` only for dayjs locale loading. Per spec: separate keys per script, no auto-transliteration.
2. **Hardcoded Cyrillic strings in components** — top offenders:
    - `frontend/src/modules/seller/pages/found/ui/page/Page.tsx:302, 315, 328, 341, 354` — Russian listing titles inside `getMockups()`. **Disappear with [A3](../easy/A3-mock-data-found.md).**
    - `frontend/src/modules/buyer/pages/listing-detail/ui/dialogs/DescriptionDrawer.tsx:48, 51` — regex literals matching `/Фото \/ Images/` and `/Продавец:/` to slice the description string. These are user-input parsing rules, but the patterns are RU-only and cause UZ descriptions to render with stray prefixes.
    - `frontend/src/modules/buyer/pages/listing-detail/ui/main/ListingMap.tsx:63-90` — Cyrillic district keys (`"сергели"`, `"мирабад"` …) in a lookup table. Data, not UI — reasonable to leave, but the lookup must accept Latin-script district names too once the parser standardises.
3. **No ICU/plural support.** The codebase uses `i18next` (typical) but no evidence of `Intl.PluralRules` or ICU MessageFormat. Spec calls out plurals: "1 объявление" / "2 объявления" / "5 объявлений" — Russian has 3 plural forms, Uzbek has 2.
4. **`toLocaleString("ru-RU")` is hardcoded** in multiple places (`PreferencesPanel.tsx:252-253`, `Page.tsx:411-412, 874-875`). Should be `toLocaleString(i18n.language)` or a shared formatter that maps locale → format.
5. **No string-length audit on UZ.** Uzbek translations average 20-40% longer than RU; cabinet card chips and bottom-sheet headers are likely to overflow. Not a code change, but a deliberate visual-pass step in the path-to-DONE.
6. **New A1-A8 strings not yet in dictionary.** Each downstream spec lists the keys it needs (e.g. A1 needs `seller.showSource` / `seller.hideSource`, A3 needs `found.loadError`, A5 needs `seller.dashboard.last7Days`, A4 will need a notification template family). Spec compliance requires these to exist in all three locales when their consumer ships.

## Path to DONE

1. **Create `uz-latn/` locale set.** Copy `uz/{admin,buyer,seller,common}.json` to `uz-latn/`; native-speaker pass to transliterate values (operational task, not engineering). Engineering-side: register the locale in `frontend/src/shared/i18n/index.ts` (or wherever `i18next.init` lives), wire the language switcher, and add the dayjs locale import (already partially loaded).
2. **Extract DescriptionDrawer regexes.** Make the patterns locale-aware: read `t("listingDetail.descriptionMarkers.photo")` and build the regex from a key list per locale. Same for "Продавец:" → `t("listingDetail.descriptionMarkers.seller")`.
3. **Plural support.** Add `i18next-icu` (or use built-in i18next plural suffix convention `{key}_zero`, `_one`, `_few`, `_many`, `_other`). Backfill ~10 plural counters: views count, contacts count, favorites count, 7-day labels (A5), notification group ("we found N new listings", A4).
4. **Locale-aware number formatting.** Replace `toLocaleString("ru-RU")` with a shared helper:

```ts
// frontend/src/shared/lib/formatNumber.ts
export const formatNumber = (n: number) =>
    n.toLocaleString(i18n.language === "uz-latn" ? "uz-Latn-UZ" : i18n.language);
```

Apply at the four known sites; grep for `"ru-RU"` to find any others.
5. **Add downstream keys as each spec lands.** Don't pre-populate every guess; add at the moment of consumption. The pre-launch sweep at the end of Block A is what catches stragglers.
6. **Visual UZ-overflow pass.** Open the seller cabinet, found page, listing-detail in `uz` locale and screenshot the longest-string regions. Adjust component sizing; this is part of the polish pass before launch, not a separate spec.

## Behaviour & invariants

- **Three locales, three sets of keys** — `ru`, `uz`, `uz-latn`. Auto-transliteration is forbidden by spec.
- **Backend always returns codes**, frontend always renders translated strings. No backend Cyrillic in any user-visible response.
- **Plural rules per locale** — Russian uses 4 categories, Uzbek 2.
- **Number/date formatters are locale-driven** — never hardcoded "ru-RU".
- **Component-level keys**, not screen-level dumps — match the existing namespace style (`seller.dashboard.totalViews`, not `dashboardScreen.line17`).

## Acceptance criteria

- `frontend/src/shared/i18n/locales/uz-latn/` exists with the four namespace files; values pass a native-speaker review.
- Switching locale in the UI changes every visible string on at least: home, listing-detail, seller-found, seller-listings, seller-create-listing.
- `grep -RnE '[А-Яа-я]' frontend/src --include="*.tsx" | grep -v node_modules` returns only **data** strings (district names, regex content where moved to the dictionary), zero **UI** strings.
- `toLocaleString("ru-RU")` does not appear in `frontend/src` outside test fixtures.
- Pluralised counters render correctly in all three locales for {0, 1, 2, 5, 21} sample inputs.
- Each downstream Block-A spec (A1, A3, A4, A5, A8) ships with its keys in all three locales.

## References

- `frontend/src/shared/i18n/locales/{ru,uz}/{admin,buyer,seller,common}.json` — current dictionaries.
- `frontend/src/modules/buyer/pages/listing-detail/ui/dialogs/DescriptionDrawer.tsx:48, 51` — regex Russian markers.
- `frontend/src/modules/buyer/pages/listing-detail/ui/main/ListingMap.tsx:63-90` — Cyrillic district lookup (data, monitor only).
- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx:302-354` — fake titles (gone with A3).
- Sites of `toLocaleString("ru-RU")` — `PreferencesPanel.tsx:252-253`, `frontend/src/modules/buyer/pages/home/ui/page/Page.tsx:411-412, 874-875`.
- Each Block-A spec lists its required new keys; consult them before declaring this done.
