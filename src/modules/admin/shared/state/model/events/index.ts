import { createEvent } from 'effector';
import type { UserFilters, ListingFilters } from '../types';

// Dashboard
export const fetchDashboardStats = createEvent();

// Users
export const fetchUsers = createEvent<UserFilters>();
export const fetchUserDetail = createEvent<string>();
export const approveUser = createEvent<{ userId: string; notes?: string }>();
export const rejectUser = createEvent<{ userId: string; notes: string }>();
export const resetUserDetail = createEvent();

// Listings
export const fetchListings = createEvent<ListingFilters>();
export const fetchListingDetail = createEvent<string>();
export const approveListing = createEvent<{ listingId: string; notes?: string }>();
export const rejectListing = createEvent<{ listingId: string; notes: string }>();
export const resetListingDetail = createEvent();
