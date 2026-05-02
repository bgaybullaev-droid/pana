import { sample } from 'effector';
import { buildQueryParams } from '@shared/api/buyerListings';
import { fetchListingsFx, toggleLikeFx } from '../effects';
import {
  pageOpened,
  loadMore,
  filtersChanged,
  searchChanged,
  resetListings,
  likeToggled,
} from '../events';
import { $listings, $page, $hasMore, $filters, $searchTerm, $isLoading } from '../stores';

// Wire .on() handlers
$listings
  .on(fetchListingsFx.doneData, (state, payload) => [...state, ...payload.listings])
  .on(toggleLikeFx.done, (state, { params: listingId, result }) =>
    state.map((listing) =>
      listing.id === listingId
        ? {
            ...listing,
            isLiked: result.liked,
            likes: result.liked ? (listing.likes || 0) + 1 : Math.max(0, (listing.likes || 0) - 1),
          }
        : listing
    )
  )
  .reset(resetListings);

$page
  .on(fetchListingsFx.done, (page) => page + 1)
  .reset(resetListings);

$hasMore
  .on(fetchListingsFx.doneData, (_, payload) => !!payload.nextPageNumber)
  .reset(resetListings);

$filters.on(filtersChanged, (state, payload) => ({ ...state, ...payload }));
$searchTerm.on(searchChanged, (_, payload) => payload);

// Reset on filter/search change
sample({
  clock: [filtersChanged, searchChanged],
  target: resetListings,
});

// Fetch on page open
sample({
  clock: pageOpened,
  source: { filters: $filters, search: $searchTerm },
  fn: ({ filters, search }) => buildQueryParams(1, filters, search),
  target: fetchListingsFx,
});

// Fetch on load more
sample({
  clock: loadMore,
  source: { page: $page, filters: $filters, search: $searchTerm, hasMore: $hasMore, isLoading: $isLoading },
  filter: ({ hasMore, isLoading }) => hasMore && !isLoading,
  fn: ({ page, filters, search }) => buildQueryParams(page, filters, search),
  target: fetchListingsFx,
});

// Refetch after filters/search reset
sample({
  clock: resetListings,
  source: { filters: $filters, search: $searchTerm },
  fn: ({ filters, search }) => buildQueryParams(1, filters, search),
  target: fetchListingsFx,
});

// Handle like toggle
sample({
  clock: likeToggled,
  target: toggleLikeFx,
});
