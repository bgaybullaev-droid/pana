/**
 * PR-G — landmarks API client tests.
 *
 * Safe-fallback contract: the autocomplete widget relies on this module
 * returning [] / null on failure rather than throwing. Also covers the
 * locale name picker.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "../client";
import {
	getLandmark,
	landmarkName,
	searchLandmarks,
	type LandmarkDetail,
	type LandmarkListItem,
} from "../landmarks";

const SAMPLE_LIST: LandmarkListItem[] = [
	{
		id: "11111111-1111-1111-1111-111111111111",
		name: "Chorsu Bazaar",
		name_uz_latn: "Chorsu bozori",
		name_uz_cyrl: "Чорсу бозори",
		category: "market",
		region: "toshkent_shahri",
		district: "shayxontohur",
		microdistrict: null,
		latitude: 41.326,
		longitude: 69.234,
	},
];

const SAMPLE_DETAIL: LandmarkDetail = {
	...SAMPLE_LIST[0],
	osm_id: "node/123",
	source: "osm",
	created_at: "2026-06-05T12:00:00Z",
	updated_at: "2026-06-05T12:00:00Z",
};

describe("searchLandmarks", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("GETs /landmarks with query params (incl. district)", async () => {
		const spy = vi
			.spyOn(apiClient, "get")
			.mockResolvedValue({ data: SAMPLE_LIST });
		await searchLandmarks({ q: "Chor", district: "shayxontohur", limit: 5 });
		expect(spy).toHaveBeenCalledWith("/landmarks", {
			params: { q: "Chor", district: "shayxontohur", limit: 5 },
		});
	});

	it("returns the list verbatim", async () => {
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: SAMPLE_LIST });
		expect(await searchLandmarks({ q: "Chor" })).toEqual(SAMPLE_LIST);
	});

	it("returns [] on network error (safe-fallback)", async () => {
		vi.spyOn(apiClient, "get").mockRejectedValue(new Error("boom"));
		expect(await searchLandmarks({ q: "anything" })).toEqual([]);
	});

	it("returns [] when backend returns null body", async () => {
		vi.spyOn(apiClient, "get").mockResolvedValue({ data: null });
		expect(await searchLandmarks()).toEqual([]);
	});
});

describe("getLandmark", () => {
	afterEach(() => {
		vi.restoreAllMocks();
	});

	it("GETs /landmarks/{id}", async () => {
		const spy = vi
			.spyOn(apiClient, "get")
			.mockResolvedValue({ data: SAMPLE_DETAIL });
		await getLandmark(SAMPLE_DETAIL.id);
		expect(spy).toHaveBeenCalledWith(`/landmarks/${SAMPLE_DETAIL.id}`);
	});

	it("returns null on error (safe-fallback)", async () => {
		vi.spyOn(apiClient, "get").mockRejectedValue(new Error("404 Not Found"));
		expect(await getLandmark("missing")).toBeNull();
	});
});

describe("landmarkName", () => {
	const item = {
		name: "Chorsu Bazaar",
		name_uz_latn: "Chorsu bozori",
		name_uz_cyrl: "Чорсу бозори",
	};

	it("picks Russian/canonical by default", () => {
		expect(landmarkName(item, "ru")).toBe("Chorsu Bazaar");
	});
	it("picks uz-latn", () => {
		expect(landmarkName(item, "uz-latn")).toBe("Chorsu bozori");
	});
	it("picks uz-cyrl", () => {
		expect(landmarkName(item, "uz-cyrl")).toBe("Чорсу бозори");
	});
	it("falls back to canonical name when a variant is missing", () => {
		expect(
			landmarkName({ name: "X", name_uz_latn: null, name_uz_cyrl: null }, "uz-cyrl"),
		).toBe("X");
	});
});
