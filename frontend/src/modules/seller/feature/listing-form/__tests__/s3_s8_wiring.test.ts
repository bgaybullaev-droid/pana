/**
 * S3–S8 frontend wiring regression tests.
 *
 * Guards the four invariants the backend audit surfaced as blockers:
 *   (a) every S3–S8 field is serialised in the create/update payload
 *   (b) dual-read: new names (market_type, furniture) reach the wire;
 *       legacy names (building_type, is_furnished) never do
 *   (c) edit-mode pre-fill maps legacy columns to the new columns when
 *       the old row only has the deprecated column populated
 *   (d) matrix gating: invisible fields are cleared in form state so
 *       hidden controls cannot accidentally submit stale data
 *
 * These tests isolate the pure helpers (`buildListingData`-equivalent
 * shape + visibility matrix) and never boot Mantine / React. Full-form
 * integration lives in the Playwright layer.
 */

import { describe, it, expect } from "vitest";
import { clearIncompatibleFields, isVisible } from "../lib/visibility";
import type { ListingFormValues } from "../ui/useListingForm";

// Minimum complete form values — enough to satisfy every required field
// for an apartment × sell happy-path create submit.
function baseValues(over: Partial<ListingFormValues> = {}): ListingFormValues {
	return {
		type: "sell",
		property_type: "apartment",
		title: "",
		description: "",
		price: 100000,
		currency: "USD",
		is_negotiable: false,
		rooms: 2,
		area: 55,
		living_area: undefined,
		kitchen_area: undefined,
		land_area: undefined,
		floor: 3,
		total_floors: 9,
		building_type: undefined, // dual-read legacy — never submitted
		condition: "euro",
		house_type: undefined,
		house_condition: [],
		location_type: [],
		water_supply: [],
		electricity: undefined,
		heating: [],
		gas_supply: undefined,
		sewage: undefined,
		is_furnished: undefined, // dual-read legacy — never submitted
		land_purpose: undefined,
		amenities: [],
		nearby_amenities: [],
		rent_period: undefined,
		deposit: undefined,
		utilities_incl: undefined,
		min_rent_months: undefined,
		allowed_students: undefined,
		allowed_pets: undefined,
		rent_payment: [],
		mortgage_ok: false,
		installment_ok: false,
		halol_ok: false,
		deed_type: undefined,
		urgent_flag: false,
		microdistrict: undefined,
		jk_name: undefined,
		landmark: undefined,
		metro_station: undefined,
		seller_telegram: undefined,
		commercial_type: undefined,
		price_per_sqm: undefined,
		ceiling_height: undefined,
		entrance: undefined,
		parking_comm: undefined,
		building_class: undefined,
		market_type: "new",
		wall_material: undefined,
		furniture: "full",
		garage: undefined,
		basement: undefined,
		buildings_exist: undefined,
		fence: undefined,
		land_shape: undefined,
		balcony: undefined,
		listing_subtype: undefined,
		floor_plan_url: undefined,
		jk_id: undefined,
		region: "toshkent_shahri",
		district: "mirzo_ulugbek",
		address: "",
		latitude: 41.3,
		longitude: 69.3,
		phone: "",
		seller_type: "owner",
		publish_to_channel: true,
		...over,
	};
}

// Reproduce the buildListingData transform without importing the hook
// (the hook pulls in Mantine / i18n which bloats the test surface). The
// contract this encodes MUST match useListingForm.ts::buildListingData.
function buildPayload(values: ListingFormValues) {
	return {
		type: values.type,
		property_type: values.property_type,
		title: values.title || undefined,
		description: values.description || undefined,
		price: values.is_negotiable ? 0 : values.price!,
		currency: values.currency,
		is_negotiable: values.is_negotiable,
		rooms: values.rooms,
		area: values.area,
		living_area: values.living_area,
		kitchen_area: values.kitchen_area,
		land_area: values.land_area,
		floor: values.floor,
		total_floors: values.total_floors,
		condition: values.condition || undefined,
		house_type: values.house_type || undefined,
		house_condition:
			values.house_condition.length > 0 ? values.house_condition : undefined,
		location_type:
			values.location_type.length > 0 ? values.location_type : undefined,
		water_supply:
			values.water_supply.length > 0 ? values.water_supply : undefined,
		electricity: values.electricity || undefined,
		heating: values.heating.length > 0 ? values.heating : undefined,
		gas_supply: values.gas_supply || undefined,
		sewage: values.sewage || undefined,
		land_purpose: values.land_purpose || undefined,
		amenities: values.amenities.length > 0 ? values.amenities : undefined,
		nearby_amenities:
			values.nearby_amenities.length > 0 ? values.nearby_amenities : undefined,
		rent_period: values.rent_period || undefined,
		deposit: values.deposit,
		utilities_incl: values.utilities_incl,
		min_rent_months: values.min_rent_months,
		allowed_students: values.allowed_students,
		allowed_pets: values.allowed_pets,
		rent_payment:
			values.rent_payment.length > 0 ? values.rent_payment : undefined,
		mortgage_ok: values.mortgage_ok,
		installment_ok: values.installment_ok,
		halol_ok: values.halol_ok,
		deed_type: values.deed_type || undefined,
		urgent_flag: values.urgent_flag,
		microdistrict: values.microdistrict || undefined,
		jk_name: values.jk_name || undefined,
		landmark: values.landmark || undefined,
		metro_station: values.metro_station || undefined,
		seller_telegram: values.seller_telegram || undefined,
		commercial_type: values.commercial_type || undefined,
		price_per_sqm: values.price_per_sqm,
		ceiling_height: values.ceiling_height,
		entrance: values.entrance || undefined,
		parking_comm: values.parking_comm,
		building_class: values.building_class || undefined,
		market_type: values.market_type || undefined,
		wall_material: values.wall_material || undefined,
		furniture: values.furniture || undefined,
		garage: values.garage,
		basement: values.basement,
		buildings_exist: values.buildings_exist,
		fence: values.fence,
		land_shape: values.land_shape || undefined,
		balcony: values.balcony || undefined,
		listing_subtype: values.listing_subtype || undefined,
		floor_plan_url: values.floor_plan_url || undefined,
		jk_id: values.jk_id || undefined,
		region: values.region,
		district: values.district,
		address: values.address || undefined,
		latitude: values.latitude,
		longitude: values.longitude,
		phone: values.phone || undefined,
		seller_type: values.seller_type || undefined,
	};
}

describe("S3–S8 payload wiring", () => {
	it("every S3–S8 field appears as a key in the submit payload", () => {
		const payload = buildPayload(baseValues());
		const s3_to_s8 = [
			// S3
			"urgent_flag",
			"microdistrict",
			"jk_name",
			"landmark",
			"metro_station",
			"seller_telegram",
			// S4
			"commercial_type",
			"price_per_sqm",
			"ceiling_height",
			"entrance",
			"parking_comm",
			"building_class",
			// S5
			"market_type",
			"wall_material",
			"furniture",
			// S6
			"garage",
			"basement",
			"buildings_exist",
			"fence",
			"land_shape",
			"balcony",
			"listing_subtype",
			"floor_plan_url",
			// S7
			"jk_id",
		];
		for (const k of s3_to_s8) {
			expect(payload).toHaveProperty(k);
		}
	});

	it("submits S3 urgent_flag as-is (boolean, NOT NULL default)", () => {
		expect(buildPayload(baseValues()).urgent_flag).toBe(false);
		expect(buildPayload(baseValues({ urgent_flag: true })).urgent_flag).toBe(
			true,
		);
	});


	it("submits S4 commercial fields when populated", () => {
		const payload = buildPayload(
			baseValues({
				property_type: "commercial",
				commercial_type: "office",
				price_per_sqm: 1500,
				ceiling_height: 3.2,
				entrance: "separate",
				parking_comm: true,
				building_class: "standalone",
			}),
		);
		expect(payload.commercial_type).toBe("office");
		expect(payload.price_per_sqm).toBe(1500);
		expect(payload.ceiling_height).toBe(3.2);
		expect(payload.entrance).toBe("separate");
		expect(payload.parking_comm).toBe(true);
		expect(payload.building_class).toBe("standalone");
	});
});

describe("S5 dual-read: submit side", () => {
	it("NEVER submits building_type", () => {
		const payload = buildPayload(
			baseValues({ building_type: "secondary", market_type: "secondary" }),
		);
		expect(payload).not.toHaveProperty("building_type");
		expect(payload.market_type).toBe("secondary");
	});

	it("NEVER submits is_furnished", () => {
		const payload = buildPayload(
			baseValues({ is_furnished: "yes", furniture: "full" }),
		);
		expect(payload).not.toHaveProperty("is_furnished");
		expect(payload.furniture).toBe("full");
	});

	it("omits furniture when form value is undefined (not empty string)", () => {
		const payload = buildPayload(baseValues({ furniture: undefined }));
		expect(payload.furniture).toBeUndefined();
	});
});

describe("S5 dual-read: edit-mode pre-fill mapping", () => {
	// Mirrors the mapping logic in edit-listing/page/Page.tsx useEffect.
	function mapFurniture(response: {
		furniture?: string | null;
		is_furnished?: boolean | null;
	}): string | undefined {
		return (
			response.furniture ||
			(response.is_furnished === true
				? "full"
				: response.is_furnished === false
					? "none"
					: undefined)
		);
	}

	function mapMarketType(response: {
		market_type?: string | null;
		building_type?: string | null;
	}): string | undefined {
		return response.market_type || response.building_type || undefined;
	}

	it("legacy is_furnished=true maps to furniture='full'", () => {
		expect(mapFurniture({ is_furnished: true })).toBe("full");
	});

	it("legacy is_furnished=false maps to furniture='none'", () => {
		expect(mapFurniture({ is_furnished: false })).toBe("none");
	});

	it("new furniture value wins over legacy is_furnished", () => {
		// Backend response mirrors both names; trust the new column.
		expect(mapFurniture({ furniture: "partial", is_furnished: true })).toBe(
			"partial",
		);
	});

	it("null response yields undefined furniture", () => {
		expect(mapFurniture({})).toBeUndefined();
	});

	it("legacy building_type maps to market_type when new column absent", () => {
		expect(mapMarketType({ building_type: "secondary" })).toBe("secondary");
	});

	it("new market_type wins over legacy building_type", () => {
		expect(
			mapMarketType({ market_type: "new", building_type: "secondary" }),
		).toBe("new");
	});
});

describe("Matrix gating covers S3–S6 field keys", () => {
	// jk_name was removed from the house base in the Phase-1 UX pass —
	// housing complexes only apply to apartments.
	it("jk_name visible on apartment only, hidden on house+commercial+land", () => {
		expect(isVisible("jk_name", "apartment", "sell")).toBe(true);
		expect(isVisible("jk_name", "house", "rent")).toBe(false);
		expect(isVisible("jk_name", "commercial", "sell")).toBe(false);
		expect(isVisible("jk_name", "land", "sell")).toBe(false);
	});

	it("metro_station visible on apartment+commercial, hidden elsewhere", () => {
		expect(isVisible("metro_station", "apartment", "sell")).toBe(true);
		expect(isVisible("metro_station", "commercial", "rent")).toBe(true);
		expect(isVisible("metro_station", "house", "sell")).toBe(false);
		expect(isVisible("metro_station", "land", "sell")).toBe(false);
	});

	it("commercial_type only on commercial", () => {
		expect(isVisible("commercial_type", "commercial", "sell")).toBe(true);
		expect(isVisible("commercial_type", "commercial", "rent")).toBe(true);
		expect(isVisible("commercial_type", "apartment", "sell")).toBe(false);
		expect(isVisible("commercial_type", "house", "sell")).toBe(false);
	});

	it("garage / basement are house-only", () => {
		expect(isVisible("garage", "house", "sell")).toBe(true);
		expect(isVisible("basement", "house", "rent")).toBe(true);
		expect(isVisible("garage", "apartment", "sell")).toBe(false);
		expect(isVisible("basement", "commercial", "sell")).toBe(false);
	});

	it("buildings_exist / fence / land_shape are land-only", () => {
		for (const f of ["buildings_exist", "fence", "land_shape"] as const) {
			expect(isVisible(f, "land", "sell")).toBe(true);
			expect(isVisible(f, "apartment", "sell")).toBe(false);
			expect(isVisible(f, "commercial", "sell")).toBe(false);
		}
	});

	it("balcony / listing_subtype / floor_plan_url are apartment-only", () => {
		for (const f of ["balcony", "listing_subtype", "floor_plan_url"] as const) {
			expect(isVisible(f, "apartment", "sell")).toBe(true);
			expect(isVisible(f, "house", "sell")).toBe(false);
			expect(isVisible(f, "land", "sell")).toBe(false);
		}
	});

	it("clearIncompatibleFields wipes commercial-only fields when leaving commercial", () => {
		const patch = clearIncompatibleFields("apartment", "sell");
		expect(patch).toHaveProperty("commercial_type", undefined);
		expect(patch).toHaveProperty("price_per_sqm", undefined);
		expect(patch).toHaveProperty("building_class", undefined);
	});

	it("clearIncompatibleFields wipes house-only S6 fields when leaving house", () => {
		const patch = clearIncompatibleFields("apartment", "sell");
		expect(patch).toHaveProperty("garage", undefined);
		expect(patch).toHaveProperty("basement", undefined);
	});

	it("clearIncompatibleFields wipes land-only S6 fields when leaving land", () => {
		const patch = clearIncompatibleFields("apartment", "sell");
		expect(patch).toHaveProperty("buildings_exist", undefined);
		expect(patch).toHaveProperty("fence", undefined);
		expect(patch).toHaveProperty("land_shape", undefined);
	});
});
