import type { FeedSort, UnifiedFeedParams } from "@shared/api/crawlerListings";
import type { HomeFilters } from "../types";

const PER_PAGE = 20;

// UI sort ids → API sort values ("recommended" maps to undefined = relevance).
const SORT_PARAM: Record<NonNullable<HomeFilters["sort"]>, FeedSort> = {
	newest: "newest",
	cheapest: "price_asc",
	expensive: "price_desc",
};

export const toFeedSort = (
	sort: HomeFilters["sort"],
): FeedSort | undefined => (sort ? SORT_PARAM[sort] : undefined);

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
	area_min: filters.area_min,
	area_max: filters.area_max,
	floor_min: filters.floor_min,
	floor_max: filters.floor_max,
	total_floors_min: filters.total_floors_min,
	total_floors_max: filters.total_floors_max,
	not_first_floor: filters.not_first_floor,
	not_last_floor: filters.not_last_floor,
	building_type: filters.building_type,
	condition: filters.condition,
	has_photo: filters.has_photo,
	posted_within: filters.posted_within,
	sort: toFeedSort(filters.sort),
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
		compare(params.district, filters.district) &&
		params.area_min === filters.area_min &&
		params.area_max === filters.area_max &&
		params.floor_min === filters.floor_min &&
		params.floor_max === filters.floor_max &&
		params.total_floors_min === filters.total_floors_min &&
		params.total_floors_max === filters.total_floors_max &&
		params.not_first_floor === filters.not_first_floor &&
		params.not_last_floor === filters.not_last_floor &&
		params.building_type === filters.building_type &&
		compare(params.condition, filters.condition) &&
		params.has_photo === filters.has_photo &&
		params.posted_within === filters.posted_within &&
		params.sort === toFeedSort(filters.sort)
	);
};
