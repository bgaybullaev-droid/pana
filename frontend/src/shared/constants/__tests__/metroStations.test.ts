import { describe, it, expect } from "vitest";
import { METRO_STATIONS, type MetroLine } from "../metroStations";

// The 12 Tashkent-city (toshkent_shahri) districts — kept in sync with the
// backend registry in app/core/regions.py. The район→метро cascade relies on
// every station resolving to one of these.
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

const LINES: MetroLine[] = ["chilonzor", "ozbekiston", "yunusobod", "ring"];

describe("METRO_STATIONS registry", () => {
	it("lists all 49 currently-operating stations", () => {
		expect(METRO_STATIONS).toHaveLength(49);
	});

	it("has a unique key per station", () => {
		const keys = METRO_STATIONS.map((s) => s.key);
		expect(new Set(keys).size).toBe(keys.length);
	});

	it("maps every station to a valid line and Tashkent district", () => {
		for (const s of METRO_STATIONS) {
			expect(LINES).toContain(s.line);
			expect(TASHKENT_DISTRICTS.has(s.district)).toBe(true);
		}
	});

	it("places every station inside the Tashkent bounding box", () => {
		for (const s of METRO_STATIONS) {
			expect(s.lat).toBeGreaterThan(41.1);
			expect(s.lat).toBeLessThan(41.45);
			expect(s.lng).toBeGreaterThan(69.15);
			expect(s.lng).toBeLessThan(69.4);
		}
	});

	it("assigns stations to the expected district (spot checks)", () => {
		const district = (key: string) =>
			METRO_STATIONS.find((s) => s.key === key)?.district;
		expect(district("chilonzor")).toBe("chilonzor");
		expect(district("minor")).toBe("yunusobod");
		expect(district("qoyliq")).toBe("bektemir");
		expect(district("yangihayot")).toBe("yangihayot");
	});
});
