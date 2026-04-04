import type { SearchParams } from "@shared/api/search";
import type { ListingFilters } from "@shared/api/types";

const PER_PAGE = 20;

export const buildSearchParams = (
	page: number,
	filters: ListingFilters,
	searchQuery: string,
	priceRange: [number, number],
): SearchParams => ({
	page,
	per_page: PER_PAGE,
	q: searchQuery || undefined,
	type: filters.type,
	property_type: filters.property_type,
	rooms: filters.rooms,
	price_min: priceRange[0] || undefined,
	price_max: priceRange[1] || undefined,
	region: filters.region,
	district: filters.district,
	sort_by: filters.sort_by,
	sort_order: filters.sort_order,
});
