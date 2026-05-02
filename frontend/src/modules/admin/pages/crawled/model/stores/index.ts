import { createStore } from 'effector';
import type { OLXListing, TelegramListing } from '@shared/api/types';
import type { CrawledStats, CrawledSource } from '../types';
import { fetchCrawledStatsFx } from '../effects';

export const $crawledStats = createStore<CrawledStats | null>(null);

export const $activeSource = createStore<CrawledSource>('all');

export const $crawledPage = createStore(1);

export const $propertyType = createStore<string | null>(null);

export const $listingType = createStore<string | null>(null);

export const $olxListings = createStore<OLXListing[]>([]);

export const $telegramListings = createStore<TelegramListing[]>([]);

export const $olxTotal = createStore(0);

export const $telegramTotal = createStore(0);

export const $olxTotalPages = createStore(1);

export const $telegramTotalPages = createStore(1);

export const $isLoadingCrawled = createStore(false);

export const $isLoadingCrawledStats = fetchCrawledStatsFx.pending;

export const $crawledError = createStore<string | null>(null);
