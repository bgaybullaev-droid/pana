import { createEffect } from 'effector';
import type { CrawlerListingFilters } from '@shared/api/types';
import {
  fetchOLXListings,
  fetchTelegramListings,
} from '@shared/api/crawlerListings';

export const fetchOLXFx = createEffect(
  (params: CrawlerListingFilters) => fetchOLXListings(params)
);

export const fetchTelegramFx = createEffect(
  (params: CrawlerListingFilters) => fetchTelegramListings(params)
);

export const fetchCrawledStatsFx = createEffect(async () => {
  const [olxRes, tgRes] = await Promise.all([
    fetchOLXListings({ page: 1, per_page: 1 }),
    fetchTelegramListings({ page: 1, per_page: 1 }),
  ]);
  return {
    olx_count: olxRes.total,
    telegram_count: tgRes.total,
  };
});
