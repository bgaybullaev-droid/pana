import type { CrawlerListingFilters } from "@shared/api/types";

const PER_PAGE = 20;

export const buildFilters = (params: {
	page: number;
	propertyType: string | null;
	listingType: string | null;
}): CrawlerListingFilters => ({
	page: params.page,
	per_page: PER_PAGE,
	property_type: params.propertyType || undefined,
	listing_type: params.listingType || undefined,
});
