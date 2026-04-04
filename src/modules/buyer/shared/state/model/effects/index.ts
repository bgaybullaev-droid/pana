import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';

export const addFavoriteFx = createEffect(async (listingId: string) => {
  await apiClient.post(`/favorites/${listingId}`);
  return listingId;
});

export const removeFavoriteFx = createEffect(async (listingId: string) => {
  await apiClient.delete(`/favorites/${listingId}`);
  return listingId;
});

export const fetchFavoriteIdsFx = createEffect(async () => {
  const response = await apiClient.get<{ ids: string[] }>('/favorites/ids');
  return response.data.ids;
});
