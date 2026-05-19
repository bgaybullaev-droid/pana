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

// =============================================================================
// Block F V2.0 (F1) — DRAFT two-step publish effects
// =============================================================================
//
// All Stage 2 polling, regeneration, and publish flow through these.
// They consume the backend endpoints from PR-F1a; the only state
// machine on the frontend lives in create-listing/model.

export interface DraftCreateResponseData {
  id: string;
  status: string;
}

export interface DraftPreviewData {
  id: string;
  status: string;
  ai_description_ru: string | null;
  ai_description_uz: string | null;
  ai_description_uz_cyrl: string | null;
  last_ai_param_snapshot: Record<string, unknown> | null;
  ai_generation_attempted_at: string | null;
}

export interface SourceTextData {
  raw_text: string | null;
  source: string | null;
}

export const createDraftListingFx = createEffect(
  async (data: ListingCreateData) => {
    const response = await apiClient.post<DraftCreateResponseData>(
      '/listings/draft',
      data,
    );
    return response.data;
  },
);

export const fetchDraftPreviewFx = createEffect(async (id: string) => {
  const response = await apiClient.get<DraftPreviewData>(
    `/listings/${id}/draft-preview`,
  );
  return response.data;
});

export const regenerateDraftFx = createEffect(
  async ({
    id,
    triggered_by = 'manual_retry',
  }: {
    id: string;
    triggered_by?: 'manual_retry' | 'param_change';
  }) => {
    const response = await apiClient.post<{ status: string }>(
      `/listings/${id}/regenerate`,
      { triggered_by },
    );
    return response.data;
  },
);

export const publishDraftFx = createEffect(
  async ({
    id,
    description,
  }: {
    id: string;
    description?: string;
  }) => {
    // PATCH /listings/{id} flips DRAFT → ACTIVE. Backend guard
    // returns 409 {error: "ai_generation_pending"} if ai_description_ru
    // is still null — the caller surfaces a toast and keeps polling.
    const body: ListingUpdateData & { status?: string } = {
      status: 'active',
    };
    if (description !== undefined) {
      body.description = description;
    }
    const response = await apiClient.patch<Listing>(
      `/listings/${id}`,
      body,
    );
    return response.data;
  },
);

export const fetchListingSourceTextFx = createEffect(async (id: string) => {
  const response = await apiClient.get<SourceTextData>(
    `/listings/${id}/source-text`,
  );
  return response.data;
});
