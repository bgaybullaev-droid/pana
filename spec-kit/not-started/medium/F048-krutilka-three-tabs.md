# Krutilka — Three Tabs (Ф-48)

**Status:** NOT STARTED — the home page is a single non-tabbed feed; no tab UI, no per-tab state stores, no Subscriptions endpoint.
**Complexity:** MEDIUM — three feed sources, per-tab state retention, no new schema, but real UX and routing work.
**Vision-doc refs:** Section 4.1 (Крутилка), Ф-48
**Why now:** Phase 1. Saved-search retention exists at the data layer but is not visually surfaced in the main feed. Adding the Subscriptions tab makes the retention loop discoverable.

## Existing context (not "done", just current state)

The home page (`frontend/src/modules/buyer/pages/home/ui/page/Page.tsx`) renders a single full-screen Swiper backed by `/listings/feed`. Vertical swipe = next listing; horizontal swipe = next photo within a listing. Filter drawer + saved-search UI live on the same page but they don't switch the *feed source* — they just filter within the one feed.

No `Tabs` component, no `$activeTab` store, no per-tab scroll retention. The vision-doc's three-tab structure is not started.

## What needs to be built

The vision doc specifies **three tabs**:

1. **Recommended** — current behaviour. Long-term goal: AI-personalised; today: chronological feed.
2. **Subscriptions** — listings matching the user's saved searches (`SavedSearch.notify_enabled` set), newest first.
3. **Search** — listings matching the *current active search* (filter drawer state).

## Goal

Tabs visible at the top of the home page; sliding between them swaps the feed source. State is preserved per-tab (you can scroll Recommended, switch to Subscriptions, switch back, and stay where you were).

## Proposed API additions

No new endpoints required. The existing endpoints cover all three feeds:

- Recommended → `GET /listings/feed`
- Subscriptions → new query: `GET /listings/feed?saved_search_ids=<csv>` or simply union of each saved search's filters server-side. Simplest path: add `GET /listings/feed/subscriptions` that joins `SavedSearch` for `current_user`, executes each filter, deduplicates and orders by `created_at DESC`.
- Search → `GET /listings/feed?<filter params>` (already works).

## Proposed frontend shape

`modules/buyer/pages/home/`:

- `model/tabs.ts` — Effector store `$activeTab: "recommended" | "subscriptions" | "search"` + per-tab feed stores.
- Tab UI at the top — Mantine `Tabs` or a custom segmented control sized for thumb reach.
- Per-tab state retention — three independent `Swiper` instances mounted but only the active one is visible; or a single Swiper whose `dataSource` is keyed by tab and remembers scroll position via state.

## Open questions

- Should the **Subscriptions** tab show only listings posted *after* the saved-search was created? (Recommended: yes, otherwise it's just a giant union.)
- "Search" tab: empty state when no filters are active — show full feed, or a CTA to open the filter drawer? (Recommended: CTA — otherwise it's identical to Recommended.)
- AI-personalised Recommended is a separate spec — see [`F077-personalization`](../../partial/hard/F077-personalization.md). For Phase 1, "Recommended" stays chronological.

## Acceptance criteria

- Three tabs render on home; switching is instant.
- Subscriptions tab is empty when the user has no saved searches; otherwise shows union of matches.
- Each tab preserves its own scroll position when switching.
- Saved-search badge from [`05-saved-searches`](../../done/medium/05-saved-searches.md) keeps working — opening the Subscriptions tab does NOT call `/saved-searches/{id}/seen`; that remains tied to the dedicated saved-search results page.
- Tab placement decided (top of page, sticky, segmented control vs. Mantine `Tabs`) and matches the existing visual language.
- Per-tab state strategy decided — three Swiper instances vs. single Swiper with keyed dataSource — and reflected in the implementation.
