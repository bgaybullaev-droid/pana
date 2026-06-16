/**
 * Block D (FU5) — admin bot search-telemetry state (read-only).
 */

import { createEffect, restore } from "effector";

import { apiClient } from "@shared/api/client";

export interface SourceBreakdown {
	source: string;
	total: number;
	empty: number;
	unrecognized: number;
	empty_pct: number;
	unrecognized_pct: number;
}

export interface UnrecognizedRow {
	raw_text: string;
	hits: number;
}

export interface RecentRow {
	created_at: string;
	source: string;
	raw_text: string;
	extracted_fields: string[];
	results_count: number;
}

export interface SearchTelemetry {
	days: number;
	since: string;
	total: number;
	by_source: SourceBreakdown[];
	top_unrecognized: UnrecognizedRow[];
	recent: RecentRow[];
}

export const fetchSearchTelemetryFx = createEffect(async (days: number) => {
	const response = await apiClient.get<SearchTelemetry>(
		`/admin/search-telemetry?days=${days}`,
	);
	return response.data;
});

export const $searchTelemetry = restore<SearchTelemetry | null>(
	fetchSearchTelemetryFx.doneData,
	null,
);
