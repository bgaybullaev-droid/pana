import { createStore } from 'effector';
import type { ListingListItem, ListingFilters } from '@shared/api/types';
import { searchFx } from '../effects';
import { resetFilters } from '../events';

export const $results = createStore<ListingListItem[]>([])
  .reset(resetFilters);

export const $page = createStore(1)
  .reset(resetFilters);

export const $hasMore = createStore(false)
  .reset(resetFilters);

export const $total = createStore(0)
  .reset(resetFilters);

export const $filters = createStore<ListingFilters>({
  type: 'sell',
  sort_by: 'created_at',
  sort_order: 'desc',
})
  .reset(resetFilters);

export const $searchQuery = createStore('')
  .reset(resetFilters);

export const $priceRange = createStore<[number, number]>([0, 500000])
  .reset(resetFilters);

export const $isLoading = searchFx.pending;

export const $hasSearched = createStore(false)
  .reset(resetFilters);
