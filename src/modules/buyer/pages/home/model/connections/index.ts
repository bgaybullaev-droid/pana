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
import { buildFeedParams } from '../lib';

// Wire .on() handlers
$page.on(fetchFeedFx.done, (_, { params }) => params.page + 1);

$filters
  .on(filtersChanged, (state, updates) => ({ ...state, ...updates }))
  .on(searchQueryChanged, (state, q) => ({ ...state, q: q || undefined }));

$rawItems.on(fetchFeedFx.doneData, (state, data) => {
  if (data.page === 1) {
    return data.items;
  }
  return [...state, ...data.items];
});

$total.on(fetchFeedFx.doneData, (_, data) => data.total);

$hasMore.on(fetchFeedFx.doneData, (_, data) => data.page < data.total_pages);

$error.on(fetchFeedFx.failData, (_, error) => getApiError(error).message);

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
