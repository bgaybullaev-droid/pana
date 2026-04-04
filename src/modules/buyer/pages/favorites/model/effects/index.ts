import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';
import type { ListingListItem, PaginatedResponse } from '@shared/api/types';

export const fetchFavoritesFx = createEffect(async () => {
  const response = await apiClient.get<PaginatedResponse<ListingListItem>>(
    '/favorites',
    { params: { per_page: 100 } }
  );
  return response.data.items;
});

export const removeFavoriteFx = createEffect(async (listingId: string) => {
  await apiClient.delete(`/favorites/${listingId}`);
  return listingId;
});
