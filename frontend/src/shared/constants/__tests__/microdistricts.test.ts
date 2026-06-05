import { describe, it, expect } from "vitest";
import { MICRODISTRICTS } from "../microdistricts";

// The 12 Tashkent-city (toshkent_shahri) districts — kept in sync with the
// backend registry in app/core/regions.py. The район→микрорайон cascade relies
// on every entry resolving to one of these.
const TASHKENT_DISTRICTS = new Set([
	"bektemir",
	"chilonzor",
	"mirobod",
	"mirzo_ulugbek",
	"olmazor",
	"sergeli",
	"shayxontohur",
	"uchtepa",
	"yakkasaroy",
	"yangihayot",
	"yashnobod",
	"yunusobod",
]);

describe("MICRODISTRICTS registry", () => {
	it("is non-empty and covers every Tashkent district", () => {
		expect(MICRODISTRICTS.length).toBeGreaterThan(0);
		const covered = new Set(MICRODISTRICTS.map((m) => m.district));
		for (const d of TASHKENT_DISTRICTS) {
			expect(covered.has(d)).toBe(true);
		}
	});

	it("maps every entry to a valid Tashkent district", () => {
		for (const m of MICRODISTRICTS) {
			expect(TASHKENT_DISTRICTS.has(m.district)).toBe(true);
		}
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

	it("places every entry inside the Tashkent bounding box", () => {
		// Wider than the metro box: microdistricts span the whole city.
		for (const m of MICRODISTRICTS) {
			expect(m.lat).toBeGreaterThan(41.1);
			expect(m.lat).toBeLessThan(41.45);
			expect(m.lng).toBeGreaterThan(69.14);
			expect(m.lng).toBeLessThan(69.41);
		}
	});
});
