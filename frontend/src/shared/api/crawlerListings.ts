import { apiClient } from './client';
import type {
  PaginatedResponse,
  TelegramListing,
  OLXListing,
  CrawlerListingFilters,
  UnifiedListing,
  UnifiedListingListItem,
} from './types';

// =============================================================================
// Unified Listing API (resolve from any source)
// =============================================================================

export const resolveListingById = async (id: string): Promise<UnifiedListing> => {
  const response = await apiClient.get<UnifiedListing>(`/listings/resolve/${id}`);
  return response.data;
};

/** Server-side ordering of the unified feed (omit for relevance ranking). */
export type FeedSort = 'newest' | 'price_asc' | 'price_desc';

export interface UnifiedFeedParams {
  page: number;
  per_page: number;
  exclude_id?: string;
  q?: string;
  type?: ('sell' | 'rent')[];
  property_type?: ('apartment' | 'house' | 'commercial' | 'land')[];
  rooms?: number[];
  price_min?: number;
  price_max?: number;
  region?: string[];
  district?: string[];
  // Wave-1 attribute filters
  area_min?: number;
  area_max?: number;
  floor_min?: number;
  floor_max?: number;
  total_floors_min?: number;
  total_floors_max?: number;
  not_first_floor?: boolean;
  not_last_floor?: boolean;
  building_type?: 'new' | 'secondary';
  condition?: string[];
  has_photo?: boolean;
  /** Freshness window in days (1 | 7 | 30). */
  posted_within?: number;
  sort?: FeedSort;
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
  if (params.type && params.type.length > 0) queryParams.type = params.type;
  if (params.property_type && params.property_type.length > 0) queryParams.property_type = params.property_type;
  if (params.rooms && params.rooms.length > 0) queryParams.rooms = params.rooms;
  if (params.price_min !== undefined) queryParams.price_min = params.price_min;
  if (params.price_max !== undefined) queryParams.price_max = params.price_max;
  if (params.region && params.region.length > 0) queryParams.region = params.region;
  if (params.district && params.district.length > 0) queryParams.district = params.district;
  if (params.area_min !== undefined) queryParams.area_min = params.area_min;
  if (params.area_max !== undefined) queryParams.area_max = params.area_max;
  if (params.floor_min !== undefined) queryParams.floor_min = params.floor_min;
  if (params.floor_max !== undefined) queryParams.floor_max = params.floor_max;
  if (params.total_floors_min !== undefined) queryParams.total_floors_min = params.total_floors_min;
  if (params.total_floors_max !== undefined) queryParams.total_floors_max = params.total_floors_max;
  if (params.not_first_floor) queryParams.not_first_floor = true;
  if (params.not_last_floor) queryParams.not_last_floor = true;
  if (params.building_type) queryParams.building_type = params.building_type;
  if (params.condition && params.condition.length > 0) queryParams.condition = params.condition;
  if (params.has_photo) queryParams.has_photo = true;
  if (params.posted_within !== undefined) queryParams.posted_within = params.posted_within;
  if (params.sort) queryParams.sort = params.sort;

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
