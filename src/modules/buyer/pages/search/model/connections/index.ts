import { sample } from 'effector';
import { $isAuthenticated } from '@shared/state/auth/model';
import { fetchFavoriteIdsFx } from '@modules/buyer/shared/state/model';
import { searchFx } from '../effects';
import {
  pageOpened,
  searchSubmitted,
  loadMore,
  filtersChanged,
  searchQueryChanged,
  priceRangeChanged,
} from '../events';
import {
  $results,
  $page,
  $hasMore,
  $total,
  $filters,
  $searchQuery,
  $priceRange,
  $isLoading,
  $hasSearched,
} from '../stores';
import { buildSearchParams } from '../lib';

// Wire .on() handlers
$results.on(searchFx.doneData, (state, data) => {
  if (data.page === 1) return data.items;
  return [...state, ...data.items];
});

$page.on(searchFx.doneData, (_, data) => data.page);

$hasMore.on(searchFx.doneData, (_, data) => data.page < data.total_pages);

$total.on(searchFx.doneData, (_, data) => data.total);

$filters.on(filtersChanged, (state, payload) => ({ ...state, ...payload }));

$searchQuery.on(searchQueryChanged, (_, q) => q);

$priceRange.on(priceRangeChanged, (_, range) => range);

$hasSearched.on(searchFx.done, () => true);

// Fetch favorite IDs on page open (only when authenticated)
sample({
  clock: pageOpened,
  source: $isAuthenticated,
  filter: (isAuthenticated: boolean) => isAuthenticated,
  target: fetchFavoriteIdsFx,
});

// Search on submit
sample({
  clock: searchSubmitted,
  source: { filters: $filters, searchQuery: $searchQuery, priceRange: $priceRange },
  fn: ({ filters, searchQuery, priceRange }) =>
    buildSearchParams(1, filters, searchQuery, priceRange),
  target: searchFx,
});

// Load more
sample({
  clock: loadMore,
  source: {
    page: $page,
    filters: $filters,
    searchQuery: $searchQuery,
    priceRange: $priceRange,
    hasMore: $hasMore,
    isLoading: $isLoading,
  },
  filter: ({ hasMore, isLoading }) => hasMore && !isLoading,
  fn: ({ page, filters, searchQuery, priceRange }) =>
    buildSearchParams(page + 1, filters, searchQuery, priceRange),
  target: searchFx,
});
