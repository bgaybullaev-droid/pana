import { createStore } from 'effector';
import type { BuyerListing, SearchHistoryItem } from '@shared/api/types';
import { searchListingsFx } from '../effects';
import { searchQueryChanged } from '../events';
import { loadHistory } from '../lib';

export const $searchQuery = createStore('').on(searchQueryChanged, (_, query) => query);

export const $searchResults = createStore<BuyerListing[]>([])
  .on(searchListingsFx.doneData, (_, results) => results)
  .reset(searchQueryChanged);

export const $searchHistory = createStore<SearchHistoryItem[]>(loadHistory());

export const $isSearching = searchListingsFx.pending;
