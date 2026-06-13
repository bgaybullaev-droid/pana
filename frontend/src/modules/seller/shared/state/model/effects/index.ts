import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';
import type { Seller, PaginatedResponse } from '@shared/api/types';
import type {
  SellerRegistrationData,
  SellerUpdateData,
  SellerListingItem,
  AutopostStatus,
  UpdatePostResponse,
} from '../types';

// Effects
export const fetchSellerProfileFx = createEffect(async () => {
  const response = await apiClient.get<Seller>('/sellers/me');
  return response.data;
});

export const registerAsSellerFx = createEffect(async (data: SellerRegistrationData) => {
  const response = await apiClient.post<Seller>('/sellers/register', data);
  return response.data;
});

export const updateSellerProfileFx = createEffect(async (data: SellerUpdateData) => {
  const response = await apiClient.patch<Seller>('/sellers/me', data);
  return response.data;
});

export const fetchSellerListingsFx = createEffect(
  async (params: { page?: number; status?: string }) => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', params.page.toString());
    if (params.status) searchParams.set('status', params.status);

    const response = await apiClient.get<PaginatedResponse<SellerListingItem>>(
      `/sellers/me/listings?${searchParams.toString()}`
    );
    return response.data;
  }
);

export const pauseListingFx = createEffect(async (listingId: string) => {
  await apiClient.patch(`/listings/${listingId}`, { status: 'paused' });
  return listingId;
});

export const activateListingFx = createEffect(async (listingId: string) => {
  await apiClient.patch(`/listings/${listingId}`, { status: 'active' });
  return listingId;
});

export const deleteListingFx = createEffect(async (listingId: string) => {
  await apiClient.delete(`/listings/${listingId}`);
  return listingId;
});

// Block D D4 — autopost (channel publishing) effects shared across the
// autoposting page, the listing form (publish gate) and "My listings"
// (stale-post update). The autoposting page re-exports these so its own
// imports do not change.
export const fetchAutopostStatusFx = createEffect(async () => {
  const response = await apiClient.get<AutopostStatus>('/seller/autopost/status');
  return response.data;
});

export const updateChannelPostFx = createEffect(
  async ({ postId, forceTextOnly }: { postId: string; forceTextOnly: boolean }) => {
    const response = await apiClient.post<UpdatePostResponse>(
      `/seller/autopost/posts/${postId}/update`,
      { force_text_only: forceTextOnly },
    );
    return response.data;
  },
);

export const recreateChannelPostFx = createEffect(async (postId: string) => {
  const response = await apiClient.post<{ result: string }>(
    `/seller/autopost/posts/${postId}/recreate`,
  );
  return response.data;
});
