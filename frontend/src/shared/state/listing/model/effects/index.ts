import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';
import type { Listing } from '@shared/api/types';
import type { ListingCreateData, ListingUpdateData, UploadImageResponse } from '../types';

export const createListingFx = createEffect(async (data: ListingCreateData) => {
  const response = await apiClient.post<Listing>('/listings', data);
  return response.data;
});

export const updateListingFx = createEffect(
  async ({ id, data }: { id: string; data: ListingUpdateData }) => {
    const response = await apiClient.patch<Listing>(`/listings/${id}`, data);
    return response.data;
  }
);

export const fetchListingForEditFx = createEffect(async (id: string) => {
  const response = await apiClient.get<Listing>(`/listings/${id}`);
  return response.data;
});

// Upload image to local storage
export const uploadImageFx = createEffect(async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post<UploadImageResponse>(
    '/uploads/image',
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  );
  return response.data;
});
