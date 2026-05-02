import { createStore } from 'effector';
import type { ListingListItem } from '@shared/api/types';
import { fetchFavoritesFx } from '../effects';

export const $favorites = createStore<ListingListItem[]>([]);

export const $isLoading = fetchFavoritesFx.pending;

export const $error = createStore<string | null>(null)
  .reset(fetchFavoritesFx);
