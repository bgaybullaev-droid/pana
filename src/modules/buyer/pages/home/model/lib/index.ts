import type { UnifiedFeedParams } from "@shared/api/crawlerListings";
import type { HomeFilters } from "../types";

const PER_PAGE = 20;

export const buildFeedParams = (
	page: number,
	filters: HomeFilters,
): UnifiedFeedParams => ({
	page,
	per_page: PER_PAGE,
	q: filters.q,
	type: filters.type,
	property_type: filters.property_type,
	rooms: filters.rooms,
	price_min: filters.price_min,
	price_max: filters.price_max,
	region: filters.region,
	district: filters.district,
});
