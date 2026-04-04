import { createEffect, sample } from 'effector';
import type { SearchHistoryItem } from '@shared/api/types';
import { searchListingsFx } from '../effects';
import {
  searchQueryChanged,
  searchSubmitted,
  historyItemRemoved,
  historyCleared,
} from '../events';
import { $searchHistory } from '../stores';
import { saveHistory, MAX_HISTORY_ITEMS } from '../lib';

// Wire .on() handlers for search history
$searchHistory
  .on(searchSubmitted, (state, query) => {
    if (!query.trim()) return state;
    const newItem: SearchHistoryItem = {
      id: Date.now().toString(),
      query: query.trim(),
      timestamp: Date.now(),
    };
    // Remove duplicates and add new item at the beginning
    const filtered = state.filter((item) => item.query.toLowerCase() !== query.toLowerCase());
    const newHistory = [newItem, ...filtered].slice(0, MAX_HISTORY_ITEMS);
    saveHistory(newHistory);
    return newHistory;
  })
  .on(historyItemRemoved, (state, id) => {
    const newHistory = state.filter((item) => item.id !== id);
    saveHistory(newHistory);
    return newHistory;
  })
  .on(historyCleared, () => {
    saveHistory([]);
    return [];
  });

// Debounced search on query change
let searchTimeout: ReturnType<typeof setTimeout>;
sample({
  clock: searchQueryChanged,
  fn: (query) => {
    clearTimeout(searchTimeout);
    return query;
  },
  target: createEffect((query: string) => {
    searchTimeout = setTimeout(() => {
      if (query.trim()) {
        searchListingsFx(query);
      }
    }, 300);
  }),
});
