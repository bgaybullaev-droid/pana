import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';
import type { BuyerListing } from '@shared/api/types';

export const searchListingsFx = createEffect(async (query: string) => {
  if (!query.trim()) return [];
  const response = await apiClient.get<{ listings: BuyerListing[] }>('/buyer/listings', {
    params: { SearchTerm: query, PageSize: 5 },
  });
  return response.data.listings;
});
