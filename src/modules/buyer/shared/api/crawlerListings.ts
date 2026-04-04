import { apiClient } from '@shared/api/client';
import type {
  PaginatedResponse,
  TelegramListing,
  OLXListing,
  CrawlerListingFilters,
  UnifiedListing,
  UnifiedListingListItem,
} from '@shared/api/types';

// =============================================================================
// Unified Listing API (resolve from any source)
// =============================================================================

export const resolveListingById = async (id: string): Promise<UnifiedListing> => {
  const response = await apiClient.get<UnifiedListing>(`/listings/resolve/${id}`);
  return response.data;
};

export interface UnifiedFeedParams {
  page: number;
  per_page: number;
  exclude_id?: string;
  q?: string;
  type?: 'sell' | 'rent';
  property_type?: 'apartment' | 'house' | 'commercial' | 'land';
  rooms?: number[];
  price_min?: number;
  price_max?: number;
  region?: string[];
  district?: string[];
}

export const fetchUnifiedFeed = async (
  params: UnifiedFeedParams
): Promise<PaginatedResponse<UnifiedListingListItem>> => {
  const queryParams: Record<string, any> = {
    page: params.page,
    per_page: params.per_page,
  };

  if (params.exclude_id) queryParams.exclude_id = params.exclude_id;
  if (params.q) queryParams.q = params.q;
  if (params.type) queryParams.type = params.type;
  if (params.property_type) queryParams.property_type = params.property_type;
  if (params.rooms && params.rooms.length > 0) queryParams.rooms = params.rooms;
  if (params.price_min !== undefined) queryParams.price_min = params.price_min;
  if (params.price_max !== undefined) queryParams.price_max = params.price_max;
  if (params.region && params.region.length > 0) queryParams.region = params.region;
  if (params.district && params.district.length > 0) queryParams.district = params.district;

  const response = await apiClient.get<PaginatedResponse<UnifiedListingListItem>>(
    '/listings/feed',
    { params: queryParams }
  );
  return response.data;
};

// =============================================================================
// Telegram Crawler API
// =============================================================================

export const fetchTelegramListings = async (
  filters: CrawlerListingFilters = {}
): Promise<PaginatedResponse<TelegramListing>> => {
  const params: Record<string, any> = {};

  if (filters.page) params.page = filters.page;
  if (filters.per_page) params.per_page = filters.per_page;
  if (filters.property_type) params.property_type = filters.property_type;
  if (filters.listing_type) params.listing_type = filters.listing_type;
  if (filters.price_min !== undefined) params.price_min = filters.price_min;
  if (filters.price_max !== undefined) params.price_max = filters.price_max;
  if (filters.rooms !== undefined) params.rooms = filters.rooms;
  if (filters.district) params.district = filters.district;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.sort_order) params.sort_order = filters.sort_order;

  const response = await apiClient.get<PaginatedResponse<TelegramListing>>(
    '/crawler/telegram/listings',
    { params }
  );
  return response.data;
};

export const fetchTelegramListingById = async (
  id: string
): Promise<TelegramListing> => {
  const response = await apiClient.get<TelegramListing>(
    `/crawler/telegram/listings/${id}`
  );
  return response.data;
};

// =============================================================================
// OLX Crawler API
// =============================================================================

export const fetchOLXListings = async (
  filters: CrawlerListingFilters = {}
): Promise<PaginatedResponse<OLXListing>> => {
  const params: Record<string, any> = {};

  if (filters.page) params.page = filters.page;
  if (filters.per_page) params.per_page = filters.per_page;
  if (filters.property_type) params.property_type = filters.property_type;
  if (filters.listing_type) params.listing_type = filters.listing_type;
  if (filters.price_min !== undefined) params.price_min = filters.price_min;
  if (filters.price_max !== undefined) params.price_max = filters.price_max;
  if (filters.rooms !== undefined) params.rooms = filters.rooms;
  if (filters.district) params.district = filters.district;
  if (filters.sort_by) params.sort_by = filters.sort_by;
  if (filters.sort_order) params.sort_order = filters.sort_order;

  const response = await apiClient.get<PaginatedResponse<OLXListing>>(
    '/crawler/olx/listings',
    { params }
  );
  return response.data;
};

export const fetchOLXListingById = async (
  id: string
): Promise<OLXListing> => {
  const response = await apiClient.get<OLXListing>(
    `/crawler/olx/listings/${id}`
  );
  return response.data;
};
