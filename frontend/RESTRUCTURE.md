# Frontend FSD Restructure Plan

## Architecture Overview

Restructured following the FSD pattern from the metadata-management project:
- **Shell app** (`app/`) — entry point, auth providers, top-level router that lazy-loads modules
- **Modules** (`modules/`) — each module is a self-contained mini-FSD app with its own `app/`, `pages/`, `feature/`, `shared/`
- **Global shared** (`shared/`) — only code used by 2+ modules

### Effector Model Split Rule

Every `model.ts` file is split into a `model/` folder:

```
model/
├── events/index.ts
├── effects/index.ts
├── stores/index.ts
├── connections/index.ts
├── types/index.ts
├── lib/index.ts
└── index.ts            ← barrel export
```

---

## Complete File Map

### `src/app/` — Shell (entry point)

```
src/app/
├── index.tsx                              ← Root App component (triggers appInitialized)
├── router/
│   ├── Router.tsx                         ← Top-level router: lazy-loads buyer/seller/admin modules
│   └── index.ts
├── providers/
│   ├── AuthProvider.tsx                   ← FROM: app/providers/AuthProvider.tsx
│   ├── TelegramProvider.tsx               ← FROM: app/providers/TelegramProvider.tsx
│   ├── useAuth.ts                         ← FROM: app/providers/useAuth.ts
│   └── useTelegram.ts                     ← FROM: app/providers/useTelegram.ts
├── styles/
│   └── theme.ts                           ← FROM: app/styles/theme.ts
├── pages/
│   └── auth/
│       ├── AuthPage.tsx                   ← FROM: pages/auth/AuthPage.tsx
│       └── index.ts                       ← FROM: pages/auth/index.ts
└── ui/
    └── layout/
        └── Layout.tsx                     ← NEW: minimal shell layout (no bottom-nav, just outlet)
```

**Router.tsx** — Only defines top-level module boundaries:
```tsx
/auth/*         → AuthPage (local)
/admin/*        → lazy(() => import('modules/admin'))
/seller/*       → lazy(() => import('modules/seller'))
/*              → lazy(() => import('modules/buyer'))
```

---

### `src/modules/buyer/` — Buyer Module

```
src/modules/buyer/
├── app/
│   ├── index.tsx                          ← Buyer App component (wraps BuyerLayout + Outlet)
│   ├── router/
│   │   ├── Router.tsx                     ← Buyer internal routes
│   │   └── index.ts
│   └── ui/
│       └── layout/
│           ├── BuyerLayout.tsx            ← FROM: widgets/layout/Layout.tsx (scroll mgmt, search drawer)
│           └── index.ts
│
├── pages/
│   ├── home/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← pageOpened, loadMore, resetListings, searchQueryChanged, filtersChanged, applyFilters, clearFilters
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchFeedFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $page, $filters, $searchQuery, $listings, $total, $hasMore, $isLoading, $error
│   │   │   ├── connections/
│   │   │   │   └── index.ts              ← sample() wiring: pageOpened→fetchFeedFx, loadMore→page+1, filtersChanged→reset+fetch, language change→refetch
│   │   │   ├── types/
│   │   │   │   └── index.ts              ← HomeFilters, HomePageState
│   │   │   ├── lib/
│   │   │   │   └── index.ts              ← helper functions
│   │   │   └── index.ts                  ← barrel export
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── HomePage.tsx           ← FROM: pages/home/index.tsx
│   │   │   │   └── index.ts
│   │   │   ├── main/
│   │   │   │   └── HomeContent.tsx        ← main content area (listing grid, empty state)
│   │   │   └── headers/
│   │   │       └── HomeHeader.tsx         ← filter chips, search bar section
│   │   └── index.ts                       ← exports { Home: { route: '/', Page } }
│   │
│   ├── listing-detail/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← pageOpened, seedListingIds, loadMore, toggleFavorite, commentAdded, ensureNearbyResolved
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchInitialListingFx, fetchFeedFx, fetchListingDetailsFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $seedIds, $initialListingId, $listingsMap, $slideIds, $page, $hasMore, $isLoading, $isLoadingMore, $error
│   │   │   ├── connections/
│   │   │   │   └── index.ts              ← pageOpened→fetchInitial, loadMore→fetchFeed, ensureNearbyResolved→fetchBatch
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── ListingDetailPage.tsx  ← FROM: pages/listing-detail/index.tsx
│   │   │   │   └── index.ts
│   │   │   ├── main/
│   │   │   │   ├── ListingSlideContent.tsx ← FROM: pages/listing-detail/ui/ListingSlideContent.tsx
│   │   │   │   ├── ListingTikTokSlider.tsx ← FROM: pages/listing-detail/ui/ListingTikTokSlider.tsx
│   │   │   │   ├── CommentItem.tsx        ← FROM: pages/listing-detail/ui/CommentItem.tsx
│   │   │   │   └── Sliders/
│   │   │   │       ├── AndroidSlider.tsx  ← FROM: pages/listing-detail/ui/Sliders/AndroidSlider.tsx
│   │   │   │       ├── IOSSlider.tsx      ← FROM: pages/listing-detail/ui/Sliders/IOSSlider.tsx
│   │   │   │       ├── SlideContent.tsx   ← FROM: pages/listing-detail/ui/Sliders/SlideContent.tsx
│   │   │   │       ├── styles.css         ← FROM: pages/listing-detail/ui/Sliders/styles.css
│   │   │   │       └── index.tsx          ← FROM: pages/listing-detail/ui/Sliders/index.tsx
│   │   │   └── dialogs/
│   │   │       ├── CommentsDrawer.tsx     ← FROM: pages/listing-detail/ui/CommentsDrawer.tsx
│   │   │       └── DescriptionDrawer.tsx  ← FROM: pages/listing-detail/ui/DescriptionDrawer.tsx
│   │   └── index.ts                       ← exports { ListingDetail: { route: '/listings/:id', Page } }
│   │
│   ├── browse/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← pageOpened, loadMore, filtersChanged, searchChanged, resetListings, likeToggled, shareClicked, messageClicked
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchListingsFx, toggleLikeFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $listings, $page, $hasMore, $filters, $searchTerm, $isLoading
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── BrowsePage.tsx         ← FROM: pages/browse/index.tsx
│   │   │   │   └── index.ts
│   │   │   └── main/
│   │   │       └── BrowseContent.tsx
│   │   └── index.ts
│   │
│   ├── listings/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← pageOpened, loadMore, filtersChanged, searchChanged, resetListings
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchListingsFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $listings, $page, $hasMore, $filters, $searchTerm, $isLoading
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── ListingsPage.tsx       ← FROM: pages/listings/index.tsx
│   │   │   │   └── index.ts
│   │   │   └── main/
│   │   │       ├── ListingsGrid.tsx       ← FROM: pages/listings/ui/ListingsGrid.tsx
│   │   │       └── ListingsGrid.css       ← FROM: pages/listings/ui/ListingsGrid.css
│   │   └── index.ts
│   │
│   ├── favorites/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← fetchFavorites, removeFavorite
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchFavoritesFx, removeFavoriteFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $favorites, $isLoading, $error
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── FavoritesPage.tsx      ← FROM: pages/favorites/index.tsx
│   │   │   │   └── index.ts
│   │   │   └── main/
│   │   │       └── FavoriteCard.tsx       ← FROM: pages/favorites/ui/FavoriteCard.tsx
│   │   └── index.ts
│   │
│   ├── notifications/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts
│   │   │   ├── effects/
│   │   │   │   └── index.ts
│   │   │   ├── stores/
│   │   │   │   └── index.ts
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── NotificationsPage.tsx  ← FROM: pages/notifications/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   ├── search/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← pageOpened, searchSubmitted, loadMore, filtersChanged, searchQueryChanged, priceRangeChanged, resetFilters
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← searchFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $results, $page, $hasMore, $total, $filters, $searchQuery, $priceRange, $isLoading, $hasSearched
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── SearchPage.tsx         ← FROM: pages/search/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   ├── profile/
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── ProfilePage.tsx        ← FROM: pages/profile/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   ├── preferences/
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── PreferencesPage.tsx    ← FROM: pages/preferences/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   ├── become-seller/
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── BecomeSellerPage.tsx   ← FROM: pages/become-seller/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   └── seller-profile/
│       ├── ui/
│       │   └── page/
│       │       ├── SellerProfilePage.tsx   ← FROM: pages/seller-profile/index.tsx
│       │       └── index.ts
│       └── index.ts
│
├── feature/
│   ├── filter/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← sortingChanged, priceRangeChanged, regionToggled, regionsSet, filtersReset, filtersApplied
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $filterState, $regions
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── FilterPanel.tsx            ← FROM: features/filter/ui/FilterPanel.tsx
│   │   │   ├── PriceSlider.tsx            ← FROM: features/filter/ui/PriceSlider.tsx
│   │   │   ├── RegionChips.tsx            ← FROM: features/filter/ui/RegionChips.tsx
│   │   │   └── SortingChips.tsx           ← FROM: features/filter/ui/SortingChips.tsx
│   │   └── index.ts
│   │
│   ├── preferences/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← preferencesLoaded
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchPreferencesFx, savePreferencesFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $preferences, $preferencesLoading
│   │   │   ├── connections/
│   │   │   │   └── index.ts              ← auto-fetch on auth, save onboarding state
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── PreferencesPanel.tsx       ← FROM: features/preferences/ui/PreferencesPanel.tsx
│   │   │   ├── PreferenceCard.tsx         ← FROM: features/preferences/ui/PreferenceCard.tsx
│   │   │   ├── ListingTypeSelector.tsx    ← FROM: features/preferences/ui/ListingTypeSelector.tsx
│   │   │   └── PropertyTypeSelector.tsx   ← FROM: features/preferences/ui/PropertyTypeSelector.tsx
│   │   └── index.ts
│   │
│   ├── search/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← searchQueryChanged, searchSubmitted, historyItemRemoved, historyCleared, resultSelected
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← searchListingsFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $searchQuery, $searchResults, $searchHistory, $isSearching
│   │   │   ├── connections/
│   │   │   │   └── index.ts              ← debounced search, history persistence
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── SearchInput.tsx            ← FROM: features/search/ui/SearchInput.tsx
│   │   │   └── SearchResults.tsx          ← FROM: features/search/ui/SearchResults.tsx
│   │   └── index.ts
│   │
│   └── spinner/
│       ├── ui/
│       │   ├── Spinner.tsx                ← FROM: widgets/spinner/Spinner.tsx (TikTok swiper)
│       │   └── ListingCard.tsx            ← FROM: widgets/spinner/ListingCard.tsx (skeleton)
│       └── index.ts
│
└── shared/
    ├── api/
    │   ├── buyerListings.ts               ← FROM: shared/api/buyerListings.ts
    │   ├── search.ts                      ← FROM: shared/api/search.ts
    │   └── crawlerListings.ts             ← FROM: shared/api/crawlerListings.ts (buyer uses unified feed)
    ├── constants/
    │   └── index.ts
    ├── lib/
    │   └── index.ts
    ├── ui/
    │   ├── BottomNavigation.tsx           ← FROM: widgets/bottom-navigation/BottomNavigation.tsx
    │   └── NavTab.tsx                     ← FROM: widgets/bottom-navigation/NavTab.tsx
    ├── state/
    │   └── model/
    │       ├── events/
    │       │   └── index.ts              ← buyer-level shared events
    │       ├── stores/
    │       │   └── index.ts              ← $favoritedIds (used across buyer pages)
    │       ├── effects/
    │       │   └── index.ts              ← addFavoriteFx, removeFavoriteFx, fetchFavoriteIdsFx
    │       ├── connections/
    │       │   └── index.ts              ← toggleFavorite logic, reset on logout
    │       ├── types/
    │       │   └── index.ts
    │       └── index.ts
    └── assets/
```

**Buyer Router.tsx** — Internal routes:
```
/               → HomePage
/listings       → ListingsPage
/listings/:id   → ListingDetailPage (full-screen, no bottom nav)
/browse         → BrowsePage
/favorites      → FavoritesPage
/notifications  → NotificationsPage
/profile        → ProfilePage
/preferences    → PreferencesPage
/become-seller  → BecomeSellerPage
/seller/:id     → SellerProfilePage (public view)
/search         → SearchPage
```

---

### `src/modules/seller/` — Seller Module

```
src/modules/seller/
├── app/
│   ├── index.tsx                          ← Seller App (wraps SellerLayout + Outlet)
│   ├── router/
│   │   ├── Router.tsx                     ← Seller internal routes
│   │   └── index.ts
│   └── ui/
│       └── layout/
│           ├── SellerLayout.tsx           ← FROM: widgets/seller-layout/SellerLayout.tsx
│           ├── SellerLoginGate.tsx        ← FROM: widgets/seller-layout/SellerLoginGate.tsx
│           └── index.ts
│
├── pages/
│   ├── dashboard/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts
│   │   │   ├── effects/
│   │   │   │   └── index.ts
│   │   │   ├── stores/
│   │   │   │   └── index.ts
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── SellerDashboardPage.tsx ← FROM: pages/seller/dashboard/index.tsx
│   │   │   │   └── index.ts
│   │   │   └── main/
│   │   │       └── QuickAction.tsx        ← FROM: pages/seller/dashboard/QuickAction.tsx
│   │   └── index.ts
│   │
│   ├── listings/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts
│   │   │   ├── effects/
│   │   │   │   └── index.ts
│   │   │   ├── stores/
│   │   │   │   └── index.ts
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── SellerListingsPage.tsx ← FROM: pages/seller/listings/index.tsx
│   │   │       └── index.ts
│   │   ├── __tests__/
│   │   │   └── getListingSource.test.ts   ← FROM: pages/seller/listings/__tests__/getListingSource.test.ts
│   │   └── index.ts
│   │
│   ├── create-listing/
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── CreateListingPage.tsx  ← FROM: pages/seller/create-listing/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   ├── edit-listing/
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── EditListingPage.tsx    ← FROM: pages/seller/edit-listing/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   ├── profile/
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── SellerProfilePage.tsx  ← FROM: pages/seller/profile/index.tsx
│   │   │   │   └── index.ts
│   │   │   └── main/
│   │   │       └── ContactRow.tsx         ← FROM: pages/seller/profile/ContactRow.tsx
│   │   └── index.ts
│   │
│   ├── register/
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── SellerRegisterPage.tsx ← FROM: pages/seller/register/index.tsx
│   │   │   │   └── index.ts
│   │   │   └── main/
│   │   │       └── BenefitRow.tsx         ← FROM: pages/seller/register/BenefitRow.tsx
│   │   └── index.ts
│   │
│   └── crawled-listings/
│       ├── model/
│       │   ├── events/
│       │   │   └── index.ts              ← pageOpened, tabChanged, pageChanged, resetState
│       │   ├── effects/
│       │   │   └── index.ts              ← fetchStatsFx, fetchOLXFx, fetchTelegramFx
│       │   ├── stores/
│       │   │   └── index.ts              ← $stats, $activeTab, $page, $olxListings, $telegramListings, $totalPages, $total, $isLoading, $isStatsLoading, $error
│       │   ├── connections/
│       │   │   └── index.ts
│       │   ├── types/
│       │   │   └── index.ts
│       │   ├── lib/
│       │   │   └── index.ts
│       │   └── index.ts
│       ├── ui/
│       │   ├── page/
│       │   │   ├── CrawledListingsPage.tsx ← FROM: pages/seller/crawled-listings/index.tsx
│       │   │   └── index.ts
│       │   └── main/
│       │       ├── OLXListingCard.tsx     ← FROM: pages/seller/crawled-listings/components/OLXListingCard.tsx
│       │       ├── TelegramListingCard.tsx ← FROM: pages/seller/crawled-listings/components/TelegramListingCard.tsx
│       │       ├── PropertyInfo.tsx       ← FROM: pages/seller/crawled-listings/components/PropertyInfo.tsx
│       │       └── getFirstImage.ts       ← FROM: pages/seller/crawled-listings/components/getFirstImage.ts
│       └── index.ts
│
├── feature/
│   └── listing-form/
│       ├── model/
│       │   ├── events/
│       │   │   └── index.ts
│       │   ├── effects/
│       │   │   └── index.ts
│       │   ├── stores/
│       │   │   └── index.ts
│       │   ├── connections/
│       │   │   └── index.ts
│       │   ├── types/
│       │   │   └── index.ts
│       │   ├── lib/
│       │   │   └── index.ts
│       │   └── index.ts
│       ├── ui/
│       │   ├── ListingFormFields.tsx      ← FROM: features/listing-form/ListingFormFields.tsx
│       │   └── useListingForm.ts          ← FROM: features/listing-form/useListingForm.ts
│       └── index.ts
│
└── shared/
    ├── api/
    │   └── sellerCrawledListings.ts       ← FROM: shared/api/sellerCrawledListings.ts
    ├── constants/
    │   └── index.ts
    ├── lib/
    │   └── index.ts
    ├── ui/
    │   └── (seller-only UI components)
    └── state/
        └── model/
            ├── events/
            │   └── index.ts              ← seller-level shared events
            ├── effects/
            │   └── index.ts              ← fetchSellerProfileFx, registerAsSellerFx, updateSellerProfileFx, fetchSellerListingsFx, pauseListingFx, activateListingFx, deleteListingFx
            ├── stores/
            │   └── index.ts              ← $sellerProfile, $sellerListings, $sellerListingsPagination, $isSellerRegistered, $profileCheckComplete, $isLoadingProfile, $isLoadingListings, $sellerError, $sellerStats
            ├── connections/
            │   └── index.ts
            ├── types/
            │   └── index.ts
            └── index.ts
```

**Seller Router.tsx** — Internal routes:
```
/seller/dashboard        → SellerDashboardPage
/seller/listings         → SellerListingsPage
/seller/crawled          → CrawledListingsPage
/seller/create           → CreateListingPage
/seller/edit/:id         → EditListingPage
/seller/profile          → SellerProfilePage
/seller/register         → SellerRegisterPage
```

---

### `src/modules/admin/` — Admin Module

```
src/modules/admin/
├── app/
│   ├── index.tsx                          ← Admin App (wraps AdminLayout + Outlet)
│   ├── router/
│   │   ├── Router.tsx                     ← Admin internal routes
│   │   └── index.ts
│   └── ui/
│       └── layout/
│           ├── AdminLayout.tsx            ← FROM: widgets/admin-layout/AdminLayout.tsx
│           └── index.ts
│
├── pages/
│   ├── dashboard/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← fetchDashboardStats
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchDashboardStatsFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $dashboardStats, $isLoadingDashboard
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   └── page/
│   │   │       ├── AdminDashboardPage.tsx ← FROM: pages/admin/dashboard/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   ├── users/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← fetchUsers, fetchUserDetail, approveUser, rejectUser, resetUserDetail
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchUsersFx, fetchUserDetailFx, approveUserFx, rejectUserFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $users, $usersPagination, $isLoadingUsers, $selectedUser, $isLoadingUserDetail
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── AdminUsersPage.tsx     ← FROM: pages/admin/users/index.tsx
│   │   │   │   └── index.ts
│   │   │   └── detail/
│   │   │       ├── AdminUserDetailPage.tsx ← FROM: pages/admin/users/detail/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   ├── listings/
│   │   ├── model/
│   │   │   ├── events/
│   │   │   │   └── index.ts              ← fetchListings, fetchListingDetail, approveListing, rejectListing, resetListingDetail
│   │   │   ├── effects/
│   │   │   │   └── index.ts              ← fetchListingsFx, fetchListingDetailFx, approveListingFx, rejectListingFx
│   │   │   ├── stores/
│   │   │   │   └── index.ts              ← $listings, $listingsPagination, $isLoadingListings, $selectedListing, $isLoadingListingDetail
│   │   │   ├── connections/
│   │   │   │   └── index.ts
│   │   │   ├── types/
│   │   │   │   └── index.ts
│   │   │   ├── lib/
│   │   │   │   └── index.ts
│   │   │   └── index.ts
│   │   ├── ui/
│   │   │   ├── page/
│   │   │   │   ├── AdminListingsPage.tsx  ← FROM: pages/admin/listings/index.tsx
│   │   │   │   └── index.ts
│   │   │   └── detail/
│   │   │       ├── AdminListingDetailPage.tsx ← FROM: pages/admin/listings/detail/index.tsx
│   │   │       └── index.ts
│   │   └── index.ts
│   │
│   └── crawled/
│       ├── model/
│       │   ├── events/
│       │   │   └── index.ts              ← pageOpened, sourceChanged, pageChanged, propertyTypeChanged, listingTypeChanged, resetCrawledState
│       │   ├── effects/
│       │   │   └── index.ts              ← fetchOLXFx, fetchTelegramFx, fetchCrawledStatsFx
│       │   ├── stores/
│       │   │   └── index.ts              ← $crawledStats, $activeSource, $crawledPage, $propertyType, $listingType, $olxListings, $telegramListings, $olxTotal, $telegramTotal, $olxTotalPages, $telegramTotalPages, $isLoadingCrawled, $isLoadingCrawledStats, $crawledError
│       │   ├── connections/
│       │   │   └── index.ts
│       │   ├── types/
│       │   │   └── index.ts
│       │   ├── lib/
│       │   │   └── index.ts
│       │   └── index.ts
│       ├── ui/
│       │   ├── page/
│       │   │   ├── AdminCrawledPage.tsx   ← FROM: pages/admin/crawled/index.tsx
│       │   │   └── index.ts
│       │   └── detail/
│       │       ├── AdminCrawledDetailPage.tsx ← FROM: pages/admin/crawled/detail/index.tsx
│       │       └── index.ts
│       └── index.ts
│
├── pages/
│   │   ...
│   └── login/
│       ├── ui/
│       │   └── page/
│       │       ├── AdminLoginPage.tsx     ← FROM: pages/admin/login/AdminLoginPage.tsx
│       │       └── index.ts              ← FROM: pages/admin/login/index.ts
│       └── index.ts
│
├── feature/
│   └── (empty for now — admin features can be added here)
│
└── shared/
    ├── api/
    │   └── index.ts                       ← admin-specific API calls (extracted from features/admin/model.ts)
    ├── constants/
    │   └── index.ts
    ├── lib/
    │   └── index.ts
    ├── ui/
    │   └── admin.css                      ← FROM: pages/admin/admin.css
    └── state/
        └── model/
            ├── events/
            │   └── index.ts              ← admin-level shared events
            ├── stores/
            │   └── index.ts              ← $adminError (shared across admin pages)
            ├── connections/
            │   └── index.ts
            ├── types/
            │   └── index.ts
            └── index.ts
```

**Admin Router.tsx** — Internal routes:
```
/admin/login             → AdminLoginPage (no layout)
/admin                   → AdminDashboardPage
/admin/users             → AdminUsersPage
/admin/users/:id         → AdminUserDetailPage
/admin/listings          → AdminListingsPage
/admin/listings/:id      → AdminListingDetailPage
/admin/crawled           → AdminCrawledPage
/admin/crawled/:source/:id → AdminCrawledDetailPage
```

---

### `src/shared/` — Global Shared (used by 2+ modules)

```
src/shared/
├── api/
│   ├── client.ts                          ← FROM: shared/api/client.ts (Axios instance, interceptors, token refresh)
│   ├── types.ts                           ← FROM: shared/api/types.ts (all shared TypeScript API types)
│   ├── comments.ts                        ← FROM: shared/api/comments.ts (used by buyer listing-detail + potentially seller)
│   └── notifications.ts                   ← FROM: shared/api/notifications.ts (used by buyer + shared polling)
│
├── ui/
│   ├── BuyerPhoneLogin.tsx                ← FROM: shared/ui/BuyerPhoneLogin.tsx
│   ├── EmptyState.tsx                     ← FROM: shared/ui/EmptyState.tsx
│   ├── FormSection.tsx                    ← FROM: shared/ui/FormSection.tsx
│   ├── GradientHeader.tsx                 ← FROM: shared/ui/GradientHeader.tsx
│   ├── LanguageSwitcher.tsx               ← FROM: shared/ui/LanguageSwitcher.tsx
│   ├── ListingImageThumbnail.tsx          ← FROM: shared/ui/ListingImageThumbnail.tsx
│   ├── LoginPromptCard.tsx                ← FROM: shared/ui/LoginPromptCard.tsx
│   ├── MobileOnlyScreen.tsx               ← FROM: shared/ui/MobileOnlyScreen.tsx
│   ├── PendingApprovalScreen.tsx          ← FROM: shared/ui/PendingApprovalScreen.tsx
│   ├── PillTabs.tsx                       ← FROM: shared/ui/PillTabs.tsx
│   ├── ProfileMenuItem.tsx                ← FROM: shared/ui/ProfileMenuItem.tsx
│   ├── RejectedAccountScreen.tsx          ← FROM: shared/ui/RejectedAccountScreen.tsx
│   ├── StatCard.tsx                       ← FROM: shared/ui/StatCard.tsx
│   ├── StatusScreen.tsx                   ← FROM: shared/ui/StatusScreen.tsx
│   └── UnauthScreen.tsx                   ← FROM: shared/ui/UnauthScreen.tsx
│
├── lib/
│   ├── index.ts                           ← FROM: shared/lib/index.ts
│   ├── auth-tokens.ts                     ← FROM: shared/lib/auth-tokens.ts
│   ├── constants.ts                       ← FROM: shared/lib/constants.ts
│   ├── crawlerAdapter.ts                  ← FROM: shared/lib/crawlerAdapter.ts
│   ├── date.ts                            ← FROM: shared/lib/date.ts
│   ├── regions.ts                         ← FROM: shared/lib/regions.ts
│   └── telegram/
│       └── types.ts                       ← FROM: shared/lib/telegram/types.ts
│
├── hooks/
│   └── useEffectorNotification.ts         ← FROM: shared/hooks/useEffectorNotification.ts
│
├── constants/
│   └── regions.ts                         ← FROM: shared/constants/regions.ts (DEDUPLICATE: merge with shared/lib/regions.ts into one file)
│
├── i18n/
│   ├── index.ts                           ← FROM: shared/i18n/index.ts
│   └── locales/
│       ├── ru/
│       │   ├── admin.json                 ← FROM: shared/i18n/locales/ru/admin.json
│       │   ├── buyer.json                 ← FROM: shared/i18n/locales/ru/buyer.json
│       │   ├── common.json                ← FROM: shared/i18n/locales/ru/common.json
│       │   └── seller.json                ← FROM: shared/i18n/locales/ru/seller.json
│       └── uz/
│           ├── admin.json                 ← FROM: shared/i18n/locales/uz/admin.json
│           ├── buyer.json                 ← FROM: shared/i18n/locales/uz/buyer.json
│           ├── common.json                ← FROM: shared/i18n/locales/uz/common.json
│           └── seller.json                ← FROM: shared/i18n/locales/uz/seller.json
│
└── state/
    ├── auth/
    │   └── model/
    │       ├── events/
    │       │   └── index.ts              ← authenticateWithTelegram, logout, setUser, requestSellerOTP, verifySellerOTP, loginWithBuyerPhone, loginAsAdmin, checkSession, devLogin
    │       ├── effects/
    │       │   └── index.ts              ← authenticateWithTelegramFx, checkSessionFx, logoutFx, loginWithBuyerPhoneFx, loginAsAdminFx, requestSellerOTPFx, verifySellerOTPFx, devLoginFx
    │       ├── stores/
    │       │   └── index.ts              ← $user, $isAuthenticated, $hasLoggedOut, $isLoading, $authError, $isSellerLoginLoading, $isBuyerLoginLoading, $isAdminLoginLoading, $sellerOTPStep, $sellerOTPPhone, $isSellerOTPLoading, $sellerOTPDevCode
    │       ├── connections/
    │       │   └── index.ts              ← auth flow wiring, token management, session check
    │       ├── types/
    │       │   └── index.ts
    │       ├── lib/
    │       │   └── index.ts
    │       └── index.ts
    │
    ├── user/
    │   └── model/
    │       ├── events/
    │       │   └── index.ts              ← fetchUserStats, startPolling, stopPolling
    │       ├── effects/
    │       │   └── index.ts              ← fetchUserStatsFx
    │       ├── stores/
    │       │   └── index.ts              ← $userStats
    │       ├── connections/
    │       │   └── index.ts              ← auto-poll every 30s, stop on logout
    │       ├── types/
    │       │   └── index.ts
    │       ├── lib/
    │       │   └── index.ts
    │       └── index.ts
    │
    └── listing/
        └── model/
            ├── events/
            │   └── index.ts              ← createListing, updateListing, fetchListingForEdit, resetCreateState, resetEditState
            ├── effects/
            │   └── index.ts              ← createListingFx, updateListingFx, fetchListingForEditFx, uploadImageFx
            ├── stores/
            │   └── index.ts              ← $createdListing, $isCreating, $createError, $isUploading, $editingListing, $isLoadingEdit, $isUpdating, $editError
            ├── connections/
            │   └── index.ts
            ├── types/
            │   └── index.ts
            ├── lib/
            │   └── index.ts
            └── index.ts
```

---

### Root files (unchanged)

```
src/
├── main.tsx                               ← FROM: main.tsx (Vite entry point)
├── index.css                              ← FROM: index.css (global styles)
└── vite-env.d.ts                          ← FROM: vite-env.d.ts
```

---

## File Migration Summary

| From | To | Action |
|---|---|---|
| `app/index.tsx` | `app/index.tsx` | Refactor: lazy-load modules |
| `app/router/index.tsx` | `app/router/Router.tsx` | Refactor: only top-level module routes |
| `app/providers/*` | `app/providers/*` | Move as-is |
| `app/styles/theme.ts` | `app/styles/theme.ts` | Move as-is |
| `pages/home/*` | `modules/buyer/pages/home/*` | Split model.ts → model/ folder |
| `pages/listing-detail/*` | `modules/buyer/pages/listing-detail/*` | Split model.ts → model/ folder |
| `pages/browse/*` | `modules/buyer/pages/browse/*` | Split model.ts → model/ folder |
| `pages/listings/*` | `modules/buyer/pages/listings/*` | Split model.ts → model/ folder |
| `pages/favorites/*` | `modules/buyer/pages/favorites/*` | Split model.ts → model/ folder |
| `pages/notifications/*` | `modules/buyer/pages/notifications/*` | Split model.ts → model/ folder |
| `pages/search/*` | `modules/buyer/pages/search/*` | Split model.ts → model/ folder |
| `pages/profile/*` | `modules/buyer/pages/profile/*` | Move |
| `pages/preferences/*` | `modules/buyer/pages/preferences/*` | Move |
| `pages/become-seller/*` | `modules/buyer/pages/become-seller/*` | Move |
| `pages/seller-profile/*` | `modules/buyer/pages/seller-profile/*` | Move |
| `pages/auth/*` | `app/pages/auth/*` | Move to shell |
| `pages/seller/dashboard/*` | `modules/seller/pages/dashboard/*` | Split model |
| `pages/seller/listings/*` | `modules/seller/pages/listings/*` | Split model |
| `pages/seller/create-listing/*` | `modules/seller/pages/create-listing/*` | Move |
| `pages/seller/edit-listing/*` | `modules/seller/pages/edit-listing/*` | Move |
| `pages/seller/profile/*` | `modules/seller/pages/profile/*` | Move |
| `pages/seller/register/*` | `modules/seller/pages/register/*` | Move |
| `pages/seller/crawled-listings/*` | `modules/seller/pages/crawled-listings/*` | Split model |
| `pages/admin/dashboard/*` | `modules/admin/pages/dashboard/*` | Split model |
| `pages/admin/users/*` | `modules/admin/pages/users/*` | Split model |
| `pages/admin/listings/*` | `modules/admin/pages/listings/*` | Split model |
| `pages/admin/crawled/*` | `modules/admin/pages/crawled/*` | Split model |
| `pages/admin/login/*` | `modules/admin/pages/login/*` | Move |
| `features/auth/model.ts` | `shared/state/auth/model/*` | Split → global state |
| `features/filter/*` | `modules/buyer/feature/filter/*` | Split model |
| `features/preferences/*` | `modules/buyer/feature/preferences/*` | Split model |
| `features/search/*` | `modules/buyer/feature/search/*` | Split model |
| `features/listing-form/*` | `modules/seller/feature/listing-form/*` | Split model |
| `features/admin/model.ts` | `modules/admin/shared/state/model/*` + pages | Split across admin pages |
| `entities/listing/index.ts` | `shared/state/listing/` | Barrel export |
| `entities/listing/model.ts` | `shared/state/listing/model/*` | Split → global state |
| `entities/listing/ui/ListingCard.tsx` | `shared/ui/ListingCard.tsx` | Move → global shared UI |
| `entities/listing/ui/MasonryListingCard.tsx` | `shared/ui/MasonryListingCard.tsx` | Move → global shared UI |
| `entities/seller/index.ts` | `modules/seller/shared/state/` | Barrel export |
| `entities/seller/model.ts` | `modules/seller/shared/state/model/*` | Split → seller state |
| `entities/user/model.ts` | `shared/state/user/model/*` | Split → global state |
| `shared/model/favorites.ts` | `modules/buyer/shared/state/model/*` | Split → buyer state |
| `pages/auth/AuthPage.tsx` | `app/pages/auth/AuthPage.tsx` | Move to shell |
| `pages/auth/index.ts` | `app/pages/auth/index.ts` | Move to shell |
| `pages/seller/listings/__tests__/getListingSource.test.ts` | `modules/seller/pages/listings/__tests__/getListingSource.test.ts` | Move with page |
| `pages/admin/login/AdminLoginPage.tsx` | `modules/admin/pages/login/ui/page/AdminLoginPage.tsx` | Move to admin |
| `pages/admin/login/index.ts` | `modules/admin/pages/login/ui/page/index.ts` | Move to admin |
| `widgets/layout/Layout.tsx` | `modules/buyer/app/ui/layout/` | Move to buyer |
| `widgets/bottom-navigation/*` | `modules/buyer/shared/ui/` | Move to buyer |
| `widgets/spinner/*` | `modules/buyer/feature/spinner/ui/` | Move to buyer |
| `widgets/seller-layout/*` | `modules/seller/app/ui/layout/` | Move to seller |
| `widgets/admin-layout/*` | `modules/admin/app/ui/layout/` | Move to admin |
| `shared/api/client.ts` | `shared/api/client.ts` | Stay global |
| `shared/api/types.ts` | `shared/api/types.ts` | Stay global |
| `shared/api/buyerListings.ts` | `modules/buyer/shared/api/` | Move to buyer |
| `shared/api/search.ts` | `modules/buyer/shared/api/` | Move to buyer |
| `shared/api/crawlerListings.ts` | `modules/buyer/shared/api/` | Move to buyer |
| `shared/api/sellerCrawledListings.ts` | `modules/seller/shared/api/` | Move to seller |
| `shared/api/comments.ts` | `shared/api/comments.ts` | Stay global |
| `shared/api/notifications.ts` | `shared/api/notifications.ts` | Stay global |
| `shared/ui/*` | `shared/ui/*` | Stay global |
| `shared/lib/*` | `shared/lib/*` | Stay global |
| `shared/hooks/*` | `shared/hooks/*` | Stay global |
| `shared/constants/*` | `shared/constants/*` | Stay global (deduplicate with lib/regions.ts) |
| `shared/i18n/*` | `shared/i18n/*` | Stay global |

---

## Vite Alias Updates

```typescript
// vite.config.ts
resolve: {
  alias: {
    '@': './src',
    '@app': './src/app',
    '@modules': './src/modules',
    '@shared': './src/shared',
  }
}
```

---

## Notes

1. **No `entities/` or `widgets/` layers** — following your metadata-management pattern:
   - Module-specific reusable components → `module/shared/ui/`
   - Module-specific reusable logic → `module/feature/`
   - Global reusable state → `shared/state/`
   - Global reusable UI → `shared/ui/`

2. **Every `model.ts` split into 6 sub-folders**: events, effects, stores, connections, types, lib

3. **Shell router only lazy-loads modules** — each module has its own internal Router.tsx

4. **Barrel exports at every level** — `index.ts` re-exports from sub-folders

5. **`feature/`** (singular) not `features/` — matching your metadata-management convention

6. **Duplicate regions file** (`shared/constants/regions.ts` vs `shared/lib/regions.ts`) will be deduplicated into one
