import { createStore } from 'effector';
import type { BuyerListing, BuyerFilterState } from '@shared/api/types';
import { fetchListingsFx } from '../effects';

export const $listings = createStore<BuyerListing[]>([]);
export const $page = createStore(1);
export const $hasMore = createStore(true);
export const $filters = createStore<BuyerFilterState>({
  sortingSelected: -1,
  priceRange: [0, 2000000],
  regions: [],
});
export const $searchTerm = createStore('');
export const $isLoading = fetchListingsFx.pending;
