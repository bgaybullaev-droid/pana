import { apiClient } from '@shared/api/client';
import type { PaginatedResponse, ListingListItem, ListingFilters } from '@shared/api/types';

export interface SearchParams extends ListingFilters {
  page?: number;
  per_page?: number;
}

export const searchListings = async (
  params: SearchParams
): Promise<PaginatedResponse<ListingListItem>> => {
  const queryParams: Record<string, any> = {};

  if (params.page) queryParams.page = params.page;
  if (params.per_page) queryParams.per_page = params.per_page;
  if (params.q) queryParams.q = params.q;
  if (params.type) queryParams.type = params.type;
  if (params.property_type) queryParams.property_type = params.property_type;
  if (params.rooms && params.rooms.length > 0) queryParams.rooms = params.rooms;
  if (params.price_min !== undefined) queryParams.price_min = params.price_min;
  if (params.price_max !== undefined) queryParams.price_max = params.price_max;
  if (params.area_min !== undefined) queryParams.area_min = params.area_min;
  if (params.area_max !== undefined) queryParams.area_max = params.area_max;
  if (params.region && params.region.length > 0) queryParams.region = params.region;
  if (params.district && params.district.length > 0) queryParams.district = params.district;
  if (params.sort_by) queryParams.sort_by = params.sort_by;
  if (params.sort_order) queryParams.sort_order = params.sort_order;

  const response = await apiClient.get<PaginatedResponse<ListingListItem>>(
    '/listings',
    { params: queryParams }
  );
  return response.data;
};
