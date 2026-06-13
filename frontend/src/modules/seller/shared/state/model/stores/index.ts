import { createStore } from 'effector';
import type { Seller } from '@shared/api/types';
import type { SellerStats, SellerListingItem, AutopostStatus } from '../types';
import { fetchAutopostStatusFx } from '../effects';

// Stores
export const $sellerProfile = createStore<Seller | null>(null);

export const $sellerListings = createStore<SellerListingItem[]>([]);

export const $sellerListingsPagination = createStore({
  page: 1,
  perPage: 20,
  total: 0,
  totalPages: 0,
});

export const $isSellerRegistered = $sellerProfile.map((profile) => profile !== null);

// Track if profile check is complete (success or failure)
export const $profileCheckComplete = createStore(false);

export const $isLoadingProfile = createStore(false);

export const $isLoadingListings = createStore(false);

export const $sellerError = createStore<string | null>(null);

// Computed stats from profile
export const $sellerStats = $sellerProfile.map((profile): SellerStats | null => {
  if (!profile) return null;
  return {
    totalListings: profile.listings_count,
    activeListings: profile.listings_count, // Will be updated when we fetch listings
    totalViews: profile.total_views,
    totalContacts: profile.total_contacts,
    totalFavorites: 0, // Not tracked in backend yet
  };
});

// Block D D4 — canonical autopost status store (fetch-only). The autoposting
// page re-exports this; the listing form reads it to gate the publish Switch.
// Connect/disconnect optimism lives in the page, which re-fetches after them.
export const $autopostStatus = createStore<AutopostStatus | null>(null).on(
  fetchAutopostStatusFx.doneData,
  (_, data) => data,
);
