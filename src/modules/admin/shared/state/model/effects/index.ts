import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';
import type {
  AdminUser,
  AdminUserListItem,
  AdminListingListItem,
  AdminListingDetail,
  AdminDashboardStats,
  PaginatedResponse,
} from '@shared/api/types';
import type { UserFilters, ListingFilters } from '../types';

// Dashboard
export const fetchDashboardStatsFx = createEffect(async () => {
  const response = await apiClient.get<AdminDashboardStats>('/admin/dashboard');
  return response.data;
});

// Users
export const fetchUsersFx = createEffect(async (params: UserFilters) => {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set('page', params.page.toString());
  if (params.approval_status) searchParams.set('approval_status', params.approval_status);
  if (params.role) searchParams.set('role', params.role);
  if (params.q) searchParams.set('q', params.q);

  const response = await apiClient.get<PaginatedResponse<AdminUserListItem>>(
    `/admin/users?${searchParams.toString()}`
  );
  return response.data;
});

export const fetchUserDetailFx = createEffect(async (userId: string) => {
  const response = await apiClient.get<AdminUser>(`/admin/users/${userId}`);
  return response.data;
});

export const approveUserFx = createEffect(
  async ({ userId, notes }: { userId: string; notes?: string }) => {
    const response = await apiClient.post<AdminUser>(`/admin/users/${userId}/approve`, { notes });
    return response.data;
  }
);

export const rejectUserFx = createEffect(
  async ({ userId, notes }: { userId: string; notes: string }) => {
    const response = await apiClient.post<AdminUser>(`/admin/users/${userId}/reject`, { notes });
    return response.data;
  }
);

// Listings
export const fetchListingsFx = createEffect(async (params: ListingFilters) => {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set('page', params.page.toString());
  if (params.moderation_status) searchParams.set('moderation_status', params.moderation_status);
  if (params.source_type) searchParams.set('source_type', params.source_type);

  const response = await apiClient.get<PaginatedResponse<AdminListingListItem>>(
    `/admin/listings?${searchParams.toString()}`
  );
  return response.data;
});

export const fetchListingDetailFx = createEffect(async (listingId: string) => {
  const response = await apiClient.get<AdminListingDetail>(`/admin/listings/${listingId}`);
  return response.data;
});

export const approveListingFx = createEffect(
  async ({ listingId, notes }: { listingId: string; notes?: string }) => {
    const response = await apiClient.post<AdminListingDetail>(
      `/admin/listings/${listingId}/approve`,
      { notes }
    );
    return response.data;
  }
);

export const rejectListingFx = createEffect(
  async ({ listingId, notes }: { listingId: string; notes: string }) => {
    const response = await apiClient.post<AdminListingDetail>(
      `/admin/listings/${listingId}/reject`,
      { notes }
    );
    return response.data;
  }
);
