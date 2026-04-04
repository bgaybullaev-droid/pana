import { apiClient } from '@shared/api/client';
import type { BuyerListingsResponse, BuyerFilterState } from '@shared/api/types';

export interface FetchBuyerListingsParams {
  page?: number;
  pageSize?: number;
  searchTerm?: string;
  categoryId?: string;
  sortingName?: number;
  minPrice?: number;
  maxPrice?: number;
  regionLocation?: string;
}

export const fetchBuyerListings = async (
  params: FetchBuyerListingsParams
): Promise<BuyerListingsResponse> => {
  const queryParams: Record<string, any> = {
    PageSize: params.pageSize || 10,
    PageNumber: params.page || 1,
  };

  if (params.searchTerm) queryParams.SearchTerm = params.searchTerm;
  if (params.categoryId) queryParams.CategoryId = params.categoryId;
  if (params.sortingName !== undefined && params.sortingName !== -1) {
    queryParams.SortingName = params.sortingName;
  }
  if (params.minPrice) queryParams.MinPrice = params.minPrice;
  if (params.maxPrice) queryParams.MaxPrice = params.maxPrice;
  if (params.regionLocation) queryParams.RegionLocation = params.regionLocation;

  const response = await apiClient.get<BuyerListingsResponse>('/buyer/listings', {
    params: queryParams,
  });
  return response.data;
};

export const toggleListingLike = async (listingId: string): Promise<{ liked: boolean }> => {
  const response = await apiClient.post<{ liked: boolean }>(`/buyer/listings/${listingId}/like`);
  return response.data;
};

export const buildQueryParams = (
  page: number,
  filters: BuyerFilterState,
  searchTerm: string
): FetchBuyerListingsParams => {
  const params: FetchBuyerListingsParams = {
    page,
    pageSize: 10,
  };

  if (searchTerm) params.searchTerm = searchTerm;
  if (filters.priceRange[0] > 0) params.minPrice = filters.priceRange[0];
  if (filters.priceRange[1] < 2000000) params.maxPrice = filters.priceRange[1];
  if (filters.sortingSelected !== -1) params.sortingName = filters.sortingSelected;
  if (filters.regions.length > 0) params.regionLocation = filters.regions[0];

  return params;
};
