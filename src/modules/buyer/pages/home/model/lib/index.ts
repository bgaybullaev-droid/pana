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

export const isParamsMatchingFilters = (
	params: UnifiedFeedParams,
	filters: HomeFilters,
): boolean => {
	// Compare all filter fields (ignore page/per_page)
	const compare = (a: any, b: any) => JSON.stringify(a) === JSON.stringify(b);

	return (
		params.q === filters.q &&
		compare(params.type, filters.type) &&
		compare(params.property_type, filters.property_type) &&
		compare(params.rooms, filters.rooms) &&
		params.price_min === filters.price_min &&
		params.price_max === filters.price_max &&
		compare(params.region, filters.region) &&
		compare(params.district, filters.district)
	);
};
