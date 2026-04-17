/**
 * PR-C — Facets API client unit tests.
 *
 * Covers:
 *   - getFacets passes params through to GET /listings/facets
 *   - safe-fallback: network/500 failure → empty object, no throw
 *   - bucketCount helper: 0 for missing dimension, 0 for missing value,
 *     correct count for present values, type-strict match on value
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../client";
import { bucketCount, getFacets } from "../facets";

describe("getFacets", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("calls GET /listings/facets with the caller's params", async () => {
		const spy = vi
			.spyOn(apiClient, "get")
			.mockResolvedValue({ data: { property_type: [] } });
		await getFacets({ type: "rent", property_type: "apartment" });
		expect(spy).toHaveBeenCalledWith("/listings/facets", {
			params: { type: "rent", property_type: "apartment" },
		});
	});

	it("returns the response data when the request succeeds", async () => {
		const sample = {
			property_type: [
				{ value: "apartment", count: 312 },
				{ value: "house", count: 98 },
			],
		};
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: sample });
		const out = await getFacets({});
		expect(out).toEqual(sample);
	});

	it("returns {} on network / server failure (safe-fallback)", async () => {
		vi.spyOn(apiClient, "get").mockRejectedValue(new Error("Network timeout"));
		const out = await getFacets({ type: "sell" });
		expect(out).toEqual({});
	});

	it("returns {} when backend returns null body", async () => {
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: null });
		expect(await getFacets()).toEqual({});
	});

	it("returns {} when backend returns undefined body", async () => {
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: undefined });
		expect(await getFacets()).toEqual({});
	});
});

describe("bucketCount", () => {
	it("returns 0 when the dimension is missing", () => {
		expect(bucketCount(undefined, "apartment")).toBe(0);
	});

	it("returns 0 when the value is missing from the distribution", () => {
		const buckets = [{ value: "apartment", count: 312 }];
		expect(bucketCount(buckets, "house")).toBe(0);
	});

	it("returns the count when the value is present", () => {
		const buckets = [
			{ value: "apartment", count: 312 },
			{ value: "house", count: 98 },
		];
		expect(bucketCount(buckets, "apartment")).toBe(312);
		expect(bucketCount(buckets, "house")).toBe(98);
	});

	it("matches strictly on value type (true !== 'true')", () => {
		const buckets = [{ value: true, count: 42 }];
		expect(bucketCount(buckets, true)).toBe(42);
		// Runtime assertion: triple-equals; "true" string must NOT match
		// the boolean true bucket. Cast because `FacetBucket["value"]`
		// accepts strings — we're exercising runtime, not the type system.
		expect(bucketCount(buckets, "true" as unknown as boolean)).toBe(0);
	});

	it("returns 0 for an empty distribution array", () => {
		expect(bucketCount([], "apartment")).toBe(0);
	});

	it("handles numeric bucket values (e.g. rooms)", () => {
		const buckets = [
			{ value: 1, count: 50 },
			{ value: 2, count: 120 },
			{ value: 3, count: 80 },
		];
		expect(bucketCount(buckets, 2)).toBe(120);
	});
});
