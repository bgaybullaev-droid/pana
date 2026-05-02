import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';
import type { Seller, PaginatedResponse } from '@shared/api/types';
import type { SellerRegistrationData, SellerUpdateData, SellerListingItem } from '../types';

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
