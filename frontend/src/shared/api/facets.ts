/**
 * PR-C — Facets API client.
 *
 * Wraps the backend's `GET /api/v1/listings/facets` endpoint. The backend
 * returns only applicable facets for the caller's (property_type, type)
 * combo; non-applicable dimensions are OMITTED entirely (not null).
 *
 * See docs/system-blueprint.md §11 for the silent-drop contract and
 * §19.3 for the response shape.
 */

import { apiClient } from "./client";

/** Single (value, count) bucket in a facet distribution. */
export interface FacetBucket {
	value: string | number | boolean;
	count: number;
}

/** Every facet key the backend may emit. Keys are OMITTED when non-applicable. */
export interface FacetsResponse {
	deal_type?: FacetBucket[];
	property_type?: FacetBucket[];
	region?: FacetBucket[];
	district?: FacetBucket[];
	rooms?: FacetBucket[];
	rent_period?: FacetBucket[];
	rent_payment?: FacetBucket[];
	mortgage_ok?: FacetBucket[];
	installment_ok?: FacetBucket[];
	halol_ok?: FacetBucket[];
	// S3–S5 additions (T-001 urgent_flag, T-009 commercial, T-006/008 dual-read)
	urgent_flag?: FacetBucket[];
	commercial_type?: FacetBucket[];
	building_class?: FacetBucket[];
	market_type?: FacetBucket[];
	furniture?: FacetBucket[];
}

/**
 * Filter params the facets endpoint accepts. Must match the
 * `/listings` query contract so the filtered base set stays identical
 * between listing rows and their facet counts.
 */
export interface FacetsQueryParams {
	q?: string;
	type?: "sell" | "rent";
	property_type?: "apartment" | "house" | "commercial" | "land";
	rooms?: number[];
	price_min?: number;
	price_max?: number;
	area_min?: number;
	area_max?: number;
	floor_min?: number;
	floor_max?: number;
	region?: string[];
	district?: string[];
	land_area_min?: number;
	land_area_max?: number;
	building_type?: string;
	condition?: string[];
	furnished?: boolean;
	amenities?: string[];
	nearby_amenities?: string[];
	rent_period?: string;
	utilities_incl?: boolean;
	min_rent_months?: number[];
	allowed_students?: boolean;
	allowed_pets?: boolean;
	rent_payment?: string[];
	deposit_min?: number;
	deposit_max?: number;
	mortgage_ok?: boolean;
	installment_ok?: boolean;
	halol_ok?: boolean;
	deed_type?: string;
	urgent_flag?: boolean;
	city?: string;
	microdistrict?: string;
	jk_name?: string;
	metro_station?: string;
	commercial_type?: string;
	building_class?: string;
	entrance?: string;
	parking_comm?: boolean;
	ceiling_height_min?: number;
	ceiling_height_max?: number;
	price_per_sqm_min?: number;
	price_per_sqm_max?: number;
	market_type?: string;
	wall_material?: string;
	furniture?: string;
	garage?: boolean;
	basement?: boolean;
	buildings_exist?: boolean;
	fence?: boolean;
	land_shape?: string;
	balcony?: string;
	listing_subtype?: string;
	jk_id?: string;
}

/**
 * Fetch facet distributions for the current filter state.
 *
 * Returns an empty object on any failure (network, 5xx, Redis miss →
 * Postgres compute error). The sidebar must degrade gracefully when
 * counts are unavailable — chips remain interactive, counts vanish.
 */
export async function getFacets(
	params: FacetsQueryParams = {},
): Promise<FacetsResponse> {
	try {
		const response = await apiClient.get<FacetsResponse>("/listings/facets", {
			params,
		});
		return response.data || {};
	} catch {
		// Safe-fallback: chips show without counts rather than throwing.
		return {};
	}
}

/**
 * Convenience: look up the count for a specific value inside a facet
 * dimension. Returns 0 when the dimension is omitted or the value is
 * missing from the distribution.
 */
export function bucketCount(
	buckets: FacetBucket[] | undefined,
	value: FacetBucket["value"],
): number {
	if (!buckets) return 0;
	const bucket = buckets.find((b) => b.value === value);
	return bucket ? bucket.count : 0;
}
