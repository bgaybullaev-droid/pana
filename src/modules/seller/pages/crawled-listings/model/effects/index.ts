import { createEffect } from 'effector';
import {
  fetchSellerCrawledStats,
  fetchSellerOLXListings,
  fetchSellerTelegramListings,
} from '@shared/api/sellerCrawledListings';

// --- Effects ---

export const fetchStatsFx = createEffect(fetchSellerCrawledStats);

export const fetchOLXFx = createEffect(
  (params: { page?: number; per_page?: number; listing_type?: string }) =>
    fetchSellerOLXListings(params),
);

export const fetchTelegramFx = createEffect(
  (params: { page?: number; per_page?: number; listing_type?: string }) =>
    fetchSellerTelegramListings(params),
);
