/**
 * PR-F — Housing Complexes API client.
 *
 * Backs the seller form's jk_id autocomplete widget. The two endpoints
 * mirror the backend in `app/api/v1/housing_complexes.py`:
 *
 *   GET  /api/v1/housing-complexes?q=&region=&limit=
 *   GET  /api/v1/housing-complexes/{id}
 *
 * Call sites:
 *   - `<HousingComplexAutocomplete>` widget in the seller listing form
 *     (coexists with free-text jk_name during the dual-column window;
 *     both jk_id and jk_name can be submitted — the backend accepts
 *     either or both).
 */

import { apiClient } from "./client";

export interface HousingComplexListItem {
	id: string;
	name: string;
	name_uz_latn?: string | null;
	name_uz_cyrl?: string | null;
	region: string | null;
	district: string | null;
	microdistrict?: string | null;
	latitude?: number | null;
	longitude?: number | null;
}

export interface HousingComplexDetail {
	id: string;
	name: string;
	name_uz_latn?: string | null;
	name_uz_cyrl?: string | null;
	developer_id: string | null;
	region: string | null;
	district: string | null;
	microdistrict?: string | null;
	latitude?: number | null;
	longitude?: number | null;
	osm_id?: string | null;
	source?: string | null;
	created_at: string;
	updated_at: string;
}

export interface HousingComplexSearchParams {
	q?: string;
	region?: string;
	district?: string;
	limit?: number;
}

/** Search housing complexes by name substring (optional region scope).
 *  Returns [] on error — the widget must degrade gracefully to
 *  free-text entry when the catalog service is unreachable. */
export async function searchHousingComplexes(
	params: HousingComplexSearchParams = {},
): Promise<HousingComplexListItem[]> {
	try {
		const response = await apiClient.get<HousingComplexListItem[]>(
			"/housing-complexes",
			{ params },
		);
		return response.data || [];
	} catch {
		return [];
	}
}

/** Fetch a single complex by id. Returns null on 404 or transport error. */
export async function getHousingComplex(
	id: string,
): Promise<HousingComplexDetail | null> {
	try {
		const response = await apiClient.get<HousingComplexDetail>(
			`/housing-complexes/${id}`,
		);
		return response.data;
	} catch {
		return null;
	}
}
