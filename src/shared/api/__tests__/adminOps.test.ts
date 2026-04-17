/**
 * PR-D — Admin Meili ops API client tests.
 *
 * Verifies:
 *   - getMeiliCounters calls the correct endpoint + returns the payload
 *   - reindexAllMeili posts and returns the aggregate result
 *   - Failures propagate (caller decides whether to show a notification)
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../client";
import {
	getMeiliCounters,
	reindexAllMeili,
	type MeiliCounters,
	type MeiliReindexResult,
} from "../adminOps";

const ZERO_COUNTERS: MeiliCounters = {
	meili_backfill_success_total: 0,
	meili_backfill_failure_total: 0,
	meili_index_success_total: 0,
	meili_index_failure_total: 0,
	meili_delete_success_total: 0,
	meili_delete_failure_total: 0,
};

describe("getMeiliCounters", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("GETs /admin/meili/counters", async () => {
		const spy = vi
			.spyOn(apiClient, "get")
			.mockResolvedValue({ data: ZERO_COUNTERS });
		await getMeiliCounters();
		expect(spy).toHaveBeenCalledWith("/admin/meili/counters");
	});

	it("returns the counter snapshot verbatim", async () => {
		const snapshot: MeiliCounters = {
			...ZERO_COUNTERS,
			meili_index_success_total: 42,
			meili_delete_failure_total: 3,
		};
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: snapshot });
		expect(await getMeiliCounters()).toEqual(snapshot);
	});

	it("propagates failures (no safe-fallback — caller handles it)", async () => {
		vi.spyOn(apiClient, "get").mockRejectedValue(
			new Error("503 Service Unavailable"),
		);
		await expect(getMeiliCounters()).rejects.toThrow("503 Service Unavailable");
	});
});

describe("reindexAllMeili", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("POSTs /admin/meili/reindex-all with no body", async () => {
		const spy = vi
			.spyOn(apiClient, "post")
			.mockResolvedValue({ data: { indexed_count: 0, failed_count: 0 } });
		await reindexAllMeili();
		expect(spy).toHaveBeenCalledWith("/admin/meili/reindex-all");
	});

	it("returns {indexed_count, failed_count} verbatim", async () => {
		const result: MeiliReindexResult = {
			indexed_count: 1234,
			failed_count: 2,
		};
		vi.spyOn(apiClient, "post").mockResolvedValue({ data: result });
		expect(await reindexAllMeili()).toEqual(result);
	});
});
