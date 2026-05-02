/**
 * PR-F — housingComplexes API client tests.
 *
 * Safe-fallback contract: the autocomplete widget relies on this module
 * returning empty array / null on failure rather than throwing. If
 * someone removes the try/catch, this test catches it.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../client";
import {
	getHousingComplex,
	searchHousingComplexes,
	type HousingComplexDetail,
	type HousingComplexListItem,
} from "../housingComplexes";

const SAMPLE_LIST: HousingComplexListItem[] = [
	{
		id: "11111111-1111-1111-1111-111111111111",
		name: "Tashkent City",
		region: "toshkent_shahri",
		district: "mirzo_ulugbek",
	},
];

const SAMPLE_DETAIL: HousingComplexDetail = {
	id: "11111111-1111-1111-1111-111111111111",
	name: "Tashkent City",
	developer_id: null,
	region: "toshkent_shahri",
	district: "mirzo_ulugbek",
	created_at: "2026-04-25T12:00:00Z",
	updated_at: "2026-04-25T12:00:00Z",
};

describe("searchHousingComplexes", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("GETs /housing-complexes with query params", async () => {
		const spy = vi
			.spyOn(apiClient, "get")
			.mockResolvedValue({ data: SAMPLE_LIST });
		await searchHousingComplexes({
			q: "Tash",
			region: "toshkent_shahri",
			limit: 5,
		});
		expect(spy).toHaveBeenCalledWith("/housing-complexes", {
			params: { q: "Tash", region: "toshkent_shahri", limit: 5 },
		});
	});

	it("returns the list verbatim", async () => {
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: SAMPLE_LIST });
		expect(await searchHousingComplexes({ q: "Tash" })).toEqual(SAMPLE_LIST);
	});

	it("returns [] on network error (safe-fallback)", async () => {
		vi.spyOn(apiClient, "get").mockRejectedValue(new Error("boom"));
		expect(await searchHousingComplexes({ q: "anything" })).toEqual([]);
	});

	it("returns [] when backend returns null body", async () => {
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: null });
		expect(await searchHousingComplexes()).toEqual([]);
	});

	it("sends no params when called with no args", async () => {
		const spy = vi.spyOn(apiClient, "get").mockResolvedValue({ data: [] });
		await searchHousingComplexes();
		expect(spy).toHaveBeenCalledWith("/housing-complexes", { params: {} });
	});
});

describe("getHousingComplex", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("GETs /housing-complexes/{id}", async () => {
		const spy = vi
			.spyOn(apiClient, "get")
			.mockResolvedValue({ data: SAMPLE_DETAIL });
		await getHousingComplex(SAMPLE_DETAIL.id);
		expect(spy).toHaveBeenCalledWith(`/housing-complexes/${SAMPLE_DETAIL.id}`);
	});

	it("returns the detail verbatim", async () => {
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: SAMPLE_DETAIL });
		expect(await getHousingComplex(SAMPLE_DETAIL.id)).toEqual(SAMPLE_DETAIL);
	});

	it("returns null on error (safe-fallback)", async () => {
		vi.spyOn(apiClient, "get").mockRejectedValue(new Error("404 Not Found"));
		expect(await getHousingComplex("missing")).toBeNull();
	});
});
