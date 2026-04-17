/**
 * PR-D — Admin Meili ops API client.
 *
 * Thin wrappers over:
 *   POST /api/v1/admin/meili/reindex-all   (backend: admin.py:651)
 *   GET  /api/v1/admin/meili/counters      (backend: admin.py:681)
 *
 * Every field in MeiliCounters mirrors the in-process counter dict on
 * `app.services.search_index._BACKFILL_COUNTERS`.
 */

import { apiClient } from "./client";

export interface MeiliReindexResult {
	indexed_count: number;
	failed_count: number;
}

export interface MeiliCounters {
	meili_backfill_success_total: number;
	meili_backfill_failure_total: number;
	meili_index_success_total: number;
	meili_index_failure_total: number;
	meili_delete_success_total: number;
	meili_delete_failure_total: number;
}

/** Runs a full-table backfill into Meilisearch. Long-running; the
 *  backend streams through batches and returns aggregate counts. */
export async function reindexAllMeili(): Promise<MeiliReindexResult> {
	const response = await apiClient.post<MeiliReindexResult>(
		"/admin/meili/reindex-all",
	);
	return response.data;
}

/** Snapshot the in-process counters. Safe to poll (no side effects). */
export async function getMeiliCounters(): Promise<MeiliCounters> {
	const response = await apiClient.get<MeiliCounters>("/admin/meili/counters");
	return response.data;
}
