import { createStore } from 'effector';
import type {
  AdminUser,
  AdminUserListItem,
  AdminListingListItem,
  AdminListingDetail,
  AdminDashboardStats,
} from '@shared/api/types';

// Dashboard
export const $dashboardStats = createStore<AdminDashboardStats | null>(null);

export const $isLoadingDashboard = createStore(false);

// Users
export const $users = createStore<AdminUserListItem[]>([]);

export const $usersPagination = createStore({
  page: 1,
  perPage: 20,
  total: 0,
  totalPages: 0,
});

export const $isLoadingUsers = createStore(false);

export const $selectedUser = createStore<AdminUser | null>(null);

export const $isLoadingUserDetail = createStore(false);

// Listings
export const $listings = createStore<AdminListingListItem[]>([]);

export const $listingsPagination = createStore({
  page: 1,
  perPage: 20,
  total: 0,
  totalPages: 0,
});

export const $isLoadingListings = createStore(false);

export const $selectedListing = createStore<AdminListingDetail | null>(null);

export const $isLoadingListingDetail = createStore(false);

// Errors
export const $adminError = createStore<string | null>(null);
