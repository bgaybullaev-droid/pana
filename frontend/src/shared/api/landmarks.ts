/**
 * PR-G — Landmarks (address-hint catalog) API client.
 *
 * Backs the seller form's `landmark` autocomplete. Mirrors the backend in
 * `app/api/v1/landmarks.py`:
 *
 *   GET  /api/v1/landmarks?q=&region=&district=&category=&limit=
 *   GET  /api/v1/landmarks/{id}
 *
 * Coexists with the free-text `Listing.landmark` column during the
 * dual-column window — both landmark_id and a free-text name can be sent.
 */

import { apiClient } from "./client";

export interface LandmarkListItem {
	id: string;
	name: string;
	name_uz_latn: string | null;
	name_uz_cyrl: string | null;
	category: string | null;
	region: string | null;
	district: string | null;
	microdistrict: string | null;
	latitude: number | null;
	longitude: number | null;
}

export interface LandmarkDetail extends LandmarkListItem {
	osm_id: string | null;
	source: string | null;
	created_at: string;
	updated_at: string;
}

export interface LandmarkSearchParams {
	q?: string;
	region?: string;
	district?: string;
	category?: string;
	limit?: number;
}

/** Pick the landmark name matching the active UI language, falling back to
 *  the canonical `name` when an Uzbek variant is missing. */
export function landmarkName(
	item: Pick<LandmarkListItem, "name" | "name_uz_latn" | "name_uz_cyrl">,
	lang: string,
): string {
	const l = (lang || "").toLowerCase();
	if (l.includes("cyrl")) return item.name_uz_cyrl || item.name;
	if (l.startsWith("uz")) return item.name_uz_latn || item.name;
	return item.name;
}

/** Search landmarks by name substring (optional region/district/category
 *  scope). Returns [] on error — the widget must degrade gracefully to
 *  free-text entry when the catalog service is unreachable. */
export async function searchLandmarks(
	params: LandmarkSearchParams = {},
): Promise<LandmarkListItem[]> {
	try {
		const response = await apiClient.get<LandmarkListItem[]>("/landmarks", {
			params,
		});
		return response.data || [];
	} catch {
		return [];
	}
}

/** Fetch a single landmark by id. Returns null on 404 or transport error. */
export async function getLandmark(id: string): Promise<LandmarkDetail | null> {
	try {
		const response = await apiClient.get<LandmarkDetail>(`/landmarks/${id}`);
		return response.data;
	} catch {
		return null;
	}
}
