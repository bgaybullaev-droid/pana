import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';
import { activityLogApi } from '@shared/api/activityLog';

export const addFavoriteFx = createEffect(async (listingId: string) => {
  await apiClient.post(`/favorites/${listingId}`);
  // Ф-78: log like event for interest vector
  activityLogApi.log({ action: 'like', listing_id: listingId });
  return listingId;
});

export const removeFavoriteFx = createEffect(async (listingId: string) => {
  await apiClient.delete(`/favorites/${listingId}`);
  activityLogApi.log({ action: 'unlike', listing_id: listingId });
  return listingId;
});

export const fetchFavoriteIdsFx = createEffect(async () => {
  const response = await apiClient.get<{ ids: string[] }>('/favorites/ids');
  return response.data.ids;
});
