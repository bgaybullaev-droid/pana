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
}
