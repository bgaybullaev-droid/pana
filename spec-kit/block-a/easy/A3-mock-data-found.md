# A3 — Remove Unsplash mock data from Found page

**Status:** PARTIAL — skeleton + honest empty-state copy already exist; an Unsplash-mock fallback overrides them when the API returns empty.
**Complexity:** EASY — delete the `getMockups()` block and flip one ternary.
**Block-A V2.0 ref:** A3 (Section "A3. Убрать mock-данные из раздела Found").
**Why now:** Phase-1 launch blocker. Mock cards on a fresh seller's first screen turn the wow-moment into "what is this".

## What's done

- **Skeletons during fetch** — `frontend/src/modules/seller/pages/found/ui/page/Page.tsx:705-713` renders 3 skeleton cards while `isLoading`.
- **Honest empty-state copy** — same file, lines 716-732, renders an icon + the text "Pока не нашли ваших объявлений в открытых источниках…" with a CTA to add a listing manually. Already hooked behind a conditional, just bypassed today.
- **Real API integration** — list is fetched from `/sellers/me/crawled/{olx,telegram}` via `frontend/src/modules/seller/shared/api/sellerCrawledListings.ts`.

## What's missing

1. **`getMockups()` is still called as a fallback.**

```tsx
// frontend/src/modules/seller/pages/found/ui/page/Page.tsx:267-559
const getMockups = (): UnifiedCard[] => {
    const olxImages = [
        "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?...",
        // 14 more Unsplash URLs
    ];
    const olxMockups: UnifiedCard[] = [
        { title: "2-комн. Квартира Юнусабадский район", ... },
        // 9 more fake OLX cards
    ];
    const tgMockups: UnifiedCard[] = [/* 10 fake Telegram cards */];
    ...
};
```

2. **The conditional that triggers it** — line 562:

```tsx
const displayedCards =
    unifiedCards.length > 0 ? unifiedCards : isLoading ? [] : getMockups();
```

When the backend returns an empty array and `isLoading === false`, the user sees 20 fake Unsplash cards. Tapping any of them runs through real claim/reject endpoints in A1, which is the worst possible interaction (success message on a non-existent listing).

3. **Empty-state branch is unreachable** — the empty-state JSX at lines 716-732 only renders when `displayedCards.length === 0`, which `getMockups()` prevents.

## Path to DONE

1. **Delete `getMockups()` and its arrays** (lines 267-559). All Unsplash URLs and the Russian-hardcoded fake titles vanish at the same time, which knocks several leaks off [A6](../medium/A6-i18n-leaks.md).
2. **Replace the ternary** at line 562:

```tsx
const displayedCards = unifiedCards;
```

3. **Verify empty-state renders** when both `olxCards` and `tgCards` are empty. The existing JSX at 716-732 is correct — confirm the conditional gate is `displayedCards.length === 0 && !isLoading && !error`.
4. **Add error-state branch.** Today the file has no explicit error rendering; if the API throws, `displayedCards` stays empty and the empty-state copy lies ("we didn't find anything" instead of "we couldn't load"). Add a sibling block:

```tsx
{error && !isLoading && (
    <ErrorState onRetry={refetch}>{t("found.loadError")}</ErrorState>
)}
```

5. **Add loading-timeout guard.** Spec says transition to error after 15s of pending. Wrap the existing query with a timeout or surface the existing axios timeout to the UI.

## Behaviour & invariants

- **Empty backend response → empty-state**, never fake cards.
- **Error response → error-state with retry**, not silent empty-state.
- **Skeleton during fetch** stays as-is; matches V1 convention used elsewhere in the seller module.
- **Cache invalidation on reject** — see [A1 medium spec](../medium/A1-claim-reject-v2.md) for how rejection must purge the local cache so a previously-rejected card doesn't reappear after re-fetch.

## Acceptance criteria

- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx` contains zero `unsplash.com` URLs.
- `getMockups` and `MOCK*` identifiers are absent from the production bundle (`grep -r "getMockups\|unsplash" frontend/src` returns nothing).
- Empty backend response renders the honest empty-state with the "Add listing" CTA.
- Backend error renders an error-state with a Retry button.
- All copy in the empty-state and error-state goes through `useTranslation` keys, not hardcoded strings (see [A6](../medium/A6-i18n-leaks.md) for the keys to add).

## References

- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx:267-559` — `getMockups()` + Unsplash arrays + Russian-hardcoded titles to delete.
- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx:562` — fallback ternary.
- `frontend/src/modules/seller/pages/found/ui/page/Page.tsx:705-732` — skeleton + empty-state JSX (kept).
- `frontend/src/modules/seller/shared/api/sellerCrawledListings.ts` — list-fetch client.
