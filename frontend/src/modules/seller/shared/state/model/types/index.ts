import type { ListingListItem } from '@shared/api/types';

// Types
export interface SellerStats {
  totalListings: number;
  activeListings: number;
  totalViews: number;
  totalContacts: number;
  totalFavorites: number;
}

export interface SellerRegistrationData {
  phone: string;
  company_name?: string;
}

export interface SellerUpdateData {
  company_name?: string;
  description?: string;
  logo_url?: string;
  email?: string;
  phone_public?: boolean;
  telegram_username?: string;
  instagram_url?: string;
  website_url?: string;
}

export interface SellerListingItem extends ListingListItem {
  status: 'active' | 'paused' | 'sold' | 'expired';
  contacts_count: number;
  source_type?: 'manual' | 'claimed' | 'parsed' | null;
  // Block D D4 — channel autopost overlay. Optional for deploy skew (a
  // frontend ahead of the backend just won't see them).
  autopost_post_id?: string | null;
  autopost_is_stale?: boolean;
}

// Block D D4 — autopost (channel publishing) shared types. Lifted here from
// the autoposting page module so the listing form (publish gate) and the
// "My listings" page (stale-post update) can consume them without a
// page→page import. The autoposting page re-exports them.
export interface AutopostStatus {
  connected: boolean;
  enabled: boolean;
  channel_username: string | null;
  channel_id: number | null;
  verified_at: string | null;
  stale_count: number;
  // Block D D4 — feature access via the realtor (Cabinet) tariff. Optional for
  // deploy skew; `=== false` means "show the tariff upsell" on the autopost page.
  subscription_active?: boolean;
  // The bot to add to the channel as admin (the real bot for this deployment).
  bot_username?: string | null;
  // Block D D4 — outcome of the most recent channel-publish attempt: `last_result`
  // is "ok" or a reason code; `last_result_at` is its ISO time. A timestamp that
  // doesn't advance after a save means the worker isn't processing (deploy issue).
  last_result?: string | null;
  last_result_at?: string | null;
}

export interface UpdatePostResponse {
  result: 'queued' | 'media_too_old' | string;
  post_age_hours?: number;
}
