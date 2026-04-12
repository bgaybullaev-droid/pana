import { createEvent, sample } from 'effector';
import { getApiError } from '@shared/api/client';
import { $isAuthenticated } from '@shared/state/auth/model';
import { fetchFavoriteIdsFx } from '@modules/buyer/shared/state/model';
import { onContentLanguageChanged } from '@shared/i18n';
import { savePreferencesFx } from '@modules/buyer/feature/preferences/model';
import { fetchFeedFx } from '../effects';
import {
  pageOpened,
  loadMore,
  resetListings,
  applyFilters,
  clearFilters,
  filtersChanged,
  searchQueryChanged,
} from '../events';
import { $page, $filters, $hasMore, $rawItems, $total, $error } from '../stores';
import { buildFeedParams, isParamsMatchingFilters } from '../lib';

// Wire .on() handlers
$filters
  .on(filtersChanged, (state, updates) => ({ ...state, ...updates }))
  .on(searchQueryChanged, (state, q) => ({ ...state, q: q || undefined }));

// Handle successful feed fetches with filter-matching guard
sample({
  clock: fetchFeedFx.done,
  source: { currentFilters: $filters, items: $rawItems },
  filter: ({ currentFilters }, { params }) => isParamsMatchingFilters(params, currentFilters),
  fn: ({ items }, { result }) => {
    if (result.page === 1) {
      return result.items || [];
    }
    // Simple deduplication just in case
    const existingIds = new Set(items.map(item => item.id));
    const newItems = result.items.filter(item => !existingIds.has(item.id));
    return [...items, ...newItems];
  },
  target: $rawItems,
});

sample({
  clock: fetchFeedFx.done,
  source: $filters,
  filter: (currentFilters, { params }) => isParamsMatchingFilters(params, currentFilters),
  fn: (_, { result }) => result.total,
  target: $total,
});

sample({
  clock: fetchFeedFx.done,
  source: $filters,
  filter: (currentFilters, { params }) => isParamsMatchingFilters(params, currentFilters),
  fn: (_, { result }) => result.page < result.total_pages,
  target: $hasMore,
});

sample({
  clock: fetchFeedFx.done,
  source: $filters,
  filter: (currentFilters, { params }) => isParamsMatchingFilters(params, currentFilters),
  fn: (_, { params }) => params.page + 1,
  target: $page,
});

sample({
  clock: fetchFeedFx.fail,
  source: $filters,
  filter: (currentFilters, { params }) => isParamsMatchingFilters(params, currentFilters),
  fn: (_, { error }) => getApiError(error).message,
  target: $error,
});

// On page open, fetch page 1 and load favorite IDs
sample({
  clock: pageOpened,
  source: $filters,
  fn: (filters) => buildFeedParams(1, filters),
  target: fetchFeedFx,
});

sample({
  clock: pageOpened,
  source: $isAuthenticated,
  filter: (isAuthenticated: boolean) => isAuthenticated,
  target: fetchFavoriteIdsFx,
});

// Apply filters - reset and fetch page 1
sample({
  clock: applyFilters,
  target: resetListings,
});

sample({
  clock: applyFilters,
  source: $filters,
  fn: (filters) => buildFeedParams(1, filters),
  target: fetchFeedFx,
});

// Clear filters - reset filters, listings, and fetch
sample({
  clock: clearFilters,
  target: resetListings,
});

sample({
  clock: clearFilters,
  fn: () => buildFeedParams(1, {}),
  target: fetchFeedFx,
});

// Load more — paginate through the unified feed
sample({
  clock: loadMore,
  source: { page: $page, hasMore: $hasMore, isLoading: fetchFeedFx.pending, filters: $filters },
  filter: ({ hasMore, isLoading }) => hasMore && !isLoading,
  fn: ({ page, filters }) => buildFeedParams(page, filters),
  target: fetchFeedFx,
});

// Re-fetch feed when content language changes
const contentLanguageChanged = createEvent();
onContentLanguageChanged(() => contentLanguageChanged());

sample({
  clock: contentLanguageChanged,
  target: resetListings,
});

sample({
  clock: contentLanguageChanged,
  source: $filters,
  fn: (filters) => buildFeedParams(1, filters),
  target: fetchFeedFx,
});

// Re-fetch feed when user preferences are saved (ranking may change)
sample({
  clock: savePreferencesFx.done,
  target: resetListings,
});

sample({
  clock: savePreferencesFx.done,
  source: $filters,
  fn: (filters) => buildFeedParams(1, filters),
  target: fetchFeedFx,
});
