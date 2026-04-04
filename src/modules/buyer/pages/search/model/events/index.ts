import { createEvent } from 'effector';
import type { ListingFilters } from '@shared/api/types';
import {
  toggleFavorite,
  $favoritedIds,
  fetchFavoriteIdsFx,
} from '@modules/buyer/shared/state/model';

export const pageOpened = createEvent();
export const searchSubmitted = createEvent();
export const loadMore = createEvent();
export const filtersChanged = createEvent<Partial<ListingFilters>>();
export const searchQueryChanged = createEvent<string>();
export const priceRangeChanged = createEvent<[number, number]>();
export const resetFilters = createEvent();
export { toggleFavorite, $favoritedIds, fetchFavoriteIdsFx };
