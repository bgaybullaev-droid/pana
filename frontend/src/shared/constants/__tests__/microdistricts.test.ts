import { describe, it, expect } from "vitest";
import { MICRODISTRICTS } from "../microdistricts";
import { REGIONS } from "../regions";

// Every district key used by a microdistrict must exist in the canonical
// region→district registry (REGIONS mirrors backend app/core/regions.py).
const ALL_DISTRICT_KEYS = new Set(Object.values(REGIONS).flat());

describe("MICRODISTRICTS registry", () => {
	it("is non-empty", () => {
		expect(MICRODISTRICTS.length).toBeGreaterThan(0);
	});

	it("maps every entry to a known district key", () => {
		for (const m of MICRODISTRICTS) {
			expect(ALL_DISTRICT_KEYS.has(m.district)).toBe(true);
		}
	});

	it("covers multiple regions across Uzbekistan", () => {
		const keyToRegion = new Map<string, string>();
		for (const [region, keys] of Object.entries(REGIONS)) {
			for (const k of keys) keyToRegion.set(k, region);
		}
		const regions = new Set(
			MICRODISTRICTS.map((m) => keyToRegion.get(m.district)),
		);
		// Sanity floor: data should span well beyond a single region.
		expect(regions.size).toBeGreaterThan(5);
	});

	it("has a non-empty name for every entry", () => {
		for (const m of MICRODISTRICTS) {
			expect(m.name.trim().length).toBeGreaterThan(0);
		}
	});

	it("has no duplicate name within a district", () => {
		const seen = new Set<string>();
		for (const m of MICRODISTRICTS) {
			const key = `${m.district}:${m.name.toLowerCase()}`;
			expect(seen.has(key)).toBe(false);
			seen.add(key);
		}
	});

	it("places every entry inside the Uzbekistan bounding box", () => {
		for (const m of MICRODISTRICTS) {
			expect(m.lat).toBeGreaterThan(37);
			expect(m.lat).toBeLessThan(46);
			expect(m.lng).toBeGreaterThan(55);
			expect(m.lng).toBeLessThan(74);
		}
	});
});
