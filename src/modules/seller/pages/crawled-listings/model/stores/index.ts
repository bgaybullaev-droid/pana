import { createStore } from 'effector';
import type { SellerCrawledStats, OLXListing, TelegramListing } from '@shared/api/types';
import { fetchStatsFx } from '../effects';

// --- Stores ---

export const $stats = createStore<SellerCrawledStats | null>(null);

export const $activeTab = createStore<'olx' | 'telegram'>('olx');

export const $page = createStore(1);

export const $olxListings = createStore<OLXListing[]>([]);

export const $telegramListings = createStore<TelegramListing[]>([]);

export const $totalPages = createStore(1);

export const $total = createStore(0);

export const $isLoading = createStore(false);

export const $isStatsLoading = fetchStatsFx.pending;

export const $error = createStore<string | null>(null);
