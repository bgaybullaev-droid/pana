/**
 * Requiredness table regression tests.
 *
 * The table in lib/requiredness.ts is the single source of truth for
 * "which fields are required": the Mantine validate object is generated
 * from it (buildValidateRules) and the section-status / progress UI reads
 * the same predicates. These tests pin:
 *   (a) validate parity with the historical inline rules (studio
 *       exemption, negotiable price, create-only commercial_type,
 *       land combos, rent_period gating)
 *   (b) section status transitions (neutral → error only after a submit
 *       attempt; complete is live; zero-required sections stay neutral)
 *   (c) progress counting incl. the photos pseudo-field and the
 *       scroll target ordering
 */

import { describe, it, expect } from "vitest";
import {
	buildValidateRules,
	fieldSection,
	getFirstIncompleteSection,
	getRequiredProgress,
	getSectionStates,
	SECTION_ORDER,
} from "../requiredness";
import type { ListingFormValues } from "../../ui/useListingForm";

// Empty form state — mirrors useListingForm initialValues.
function emptyValues(
	over: Partial<ListingFormValues> = {},
): ListingFormValues {
	return {
		type: "sell",
		property_type: "apartment",
		title: "",
		description: "",
		price: undefined,
		currency: "USD",
		is_negotiable: false,
		rooms: undefined,
		area: undefined,
		living_area: undefined,
		kitchen_area: undefined,
		land_area: undefined,
		floor: undefined,
		total_floors: undefined,
		building_type: undefined,
		condition: undefined,
		house_type: undefined,
		house_condition: [],
		location_type: [],
		water_supply: [],
		electricity: undefined,
		heating: [],
		gas_supply: undefined,
		sewage: undefined,
		is_furnished: undefined,
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
		market_type: undefined,
		wall_material: undefined,
		furniture: undefined,
		garage: undefined,
		basement: undefined,
		buildings_exist: undefined,
		fence: undefined,
		land_shape: undefined,
		balcony: undefined,
		listing_subtype: undefined,
		floor_plan_url: undefined,
		jk_id: undefined,
		region: "",
		district: "",
		address: "",
		latitude: undefined,
		longitude: undefined,
		phone: "",
		seller_type: "",
		publish_to_channel: true,
		...over,
	};
}

// Fully-filled apartment × sell values — the happy path.
function filledApartment(
	over: Partial<ListingFormValues> = {},
): ListingFormValues {
	return emptyValues({
		price: 100000,
		rooms: 2,
		area: 55,
		floor: 3,
		total_floors: 9,
		condition: "euro",
		market_type: "new",
		furniture: "full",
		region: "toshkent_shahri",
		district: "mirzo_ulugbek",
		latitude: 41.3,
		longitude: 69.3,
		...over,
	});
}

// Runs every generated rule and returns the error keys it produced
// (the identity `t` makes errors equal to their i18n keys).
function validationErrors(
	values: ListingFormValues,
	mode: "create" | "edit" = "create",
): string[] {
	const rules = buildValidateRules(mode, (k) => k);
	return Object.values(rules)
		.map((rule) => rule(undefined, values))
		.filter((e): e is string => e !== null)
		.sort();
}

describe("buildValidateRules — parity with the historical inline rules", () => {
	it("empty apartment × sell create reports the full required set", () => {
		expect(validationErrors(emptyValues())).toEqual(
			[
				"validation.priceRequired",
				"validation.roomsRequired",
				"validation.areaRequired",
				"validation.floorRequired",
				"validation.totalFloorsRequired",
				"validation.buildingTypeRequired",
				"validation.conditionRequired",
				"validation.furnishedRequired",
				"validation.regionRequired",
				"validation.districtRequired",
				"validation.mapRequired",
			].sort(),
		);
	});

	it("fully filled apartment × sell passes", () => {
		expect(validationErrors(filledApartment())).toEqual([]);
	});

	it("studio exemption — no rooms error for listing_subtype=studio", () => {
		const errors = validationErrors(
			emptyValues({ listing_subtype: "studio" }),
		);
		expect(errors).not.toContain("validation.roomsRequired");
	});

	it("negotiable price — no price error", () => {
		const errors = validationErrors(emptyValues({ is_negotiable: true }));
		expect(errors).not.toContain("validation.priceRequired");
	});

	it("commercial_type is required on create but not on edit", () => {
		const values = emptyValues({ property_type: "commercial" });
		expect(validationErrors(values, "create")).toContain(
			"validation.commercialTypeRequired",
		);
		expect(validationErrors(values, "edit")).not.toContain(
			"validation.commercialTypeRequired",
		);
	});

	it("land × sell only requires price + location", () => {
		expect(validationErrors(emptyValues({ property_type: "land" }))).toEqual(
			[
				"validation.priceRequired",
				"validation.regionRequired",
				"validation.districtRequired",
				"validation.mapRequired",
			].sort(),
		);
	});

	it("land × rent is legal and requires rent_period like any rental", () => {
		const errors = validationErrors(
			emptyValues({ property_type: "land", type: "rent" }),
		);
		expect(errors).toContain("validation.rentPeriodRequired");
		expect(
			validationErrors(
				emptyValues({
					property_type: "land",
					type: "rent",
					price: 500,
					rent_period: "daily",
					region: "toshkent_shahri",
					district: "mirzo_ulugbek",
					latitude: 41.3,
				}),
			),
		).toEqual([]);
	});

	it("apartment × rent requires rent_period", () => {
		const errors = validationErrors(filledApartment({ type: "rent" }));
		expect(errors).toEqual(["validation.rentPeriodRequired"]);
	});

	it("daily rent does not require min_rent_months", () => {
		const errors = validationErrors(
			filledApartment({ type: "rent", rent_period: "daily" }),
		);
		expect(errors).toEqual([]);
	});

	it("long_term rent requires min_rent_months", () => {
		const errors = validationErrors(
			filledApartment({ type: "rent", rent_period: "long_term" }),
		);
		expect(errors).toEqual(["validation.minRentMonthsRequired"]);
		expect(
			validationErrors(
				filledApartment({
					type: "rent",
					rent_period: "long_term",
					min_rent_months: 6,
				}),
			),
		).toEqual([]);
	});
});

describe("fieldSection — furniture is the only dynamic assignment", () => {
	it("furniture lives in houseAttributes for house, aptAttributes otherwise", () => {
		expect(
			fieldSection("furniture", emptyValues({ property_type: "house" })),
		).toBe("houseAttributes");
		expect(fieldSection("furniture", emptyValues())).toBe("aptAttributes");
		expect(
			fieldSection(
				"furniture",
				emptyValues({ property_type: "commercial" }),
			),
		).toBe("aptAttributes");
	});
});

describe("getSectionStates", () => {
	it("incomplete sections stay neutral before the first submit attempt", () => {
		const states = getSectionStates(emptyValues(), "create", 0, false);
		for (const key of SECTION_ORDER) {
			expect(states[key].status).not.toBe("error");
		}
		expect(states.parameters.status).toBe("neutral");
		expect(states.parameters.remaining).toBe(4); // rooms/area/floor/total_floors
	});

	it("incomplete sections turn error after a submit attempt", () => {
		const states = getSectionStates(emptyValues(), "create", 0, true);
		expect(states.photos.status).toBe("error");
		expect(states.parameters.status).toBe("error");
		expect(states.location.status).toBe("error");
		expect(states.location.remaining).toBe(3); // region/district/latitude
	});

	it("complete sections are green regardless of submitAttempted", () => {
		const values = filledApartment();
		const before = getSectionStates(values, "create", 3, false);
		const after = getSectionStates(values, "create", 3, true);
		for (const states of [before, after]) {
			expect(states.photos.status).toBe("complete");
			expect(states.parameters.status).toBe("complete");
			expect(states.aptAttributes.status).toBe("complete");
			expect(states.location.status).toBe("complete");
			expect(states.price.status).toBe("complete");
		}
	});

	it("sections without required fields are always neutral", () => {
		const states = getSectionStates(emptyValues(), "create", 0, true);
		expect(states.description.status).toBe("neutral");
		expect(states.contact.status).toBe("neutral");
		expect(states.amenities.status).toBe("neutral");
		expect(states.utilities.status).toBe("neutral");
		// The Type section hosts `type` (pre-filled) plus the lifted
		// market_type classifier (empty on a fresh apartment form) →
		// error once a submit was attempted, never neutral.
		expect(states.type.status).toBe("error");
	});

	it("commercial_type counts in the Type section (create-only)", () => {
		const values = emptyValues({ property_type: "commercial" });
		// The classifier was lifted into the Type section, so the
		// commercial section itself hosts no required fields → always
		// neutral in both modes.
		expect(getSectionStates(values, "edit", 0, true).commercial.status).toBe(
			"neutral",
		);
		expect(
			getSectionStates(values, "create", 0, true).commercial.status,
		).toBe("neutral");
		// Its create-only requiredness surfaces in the Type section.
		expect(getSectionStates(values, "create", 0, true).type.status).toBe(
			"error",
		);
		expect(getSectionStates(values, "edit", 0, true).type.status).toBe(
			"complete",
		);
	});

	it("furniture counts toward houseAttributes for houses (no double count)", () => {
		const values = emptyValues({ property_type: "house" });
		const states = getSectionStates(values, "create", 0, true);
		expect(states.houseAttributes.total).toBe(1); // furniture only
		// market_type/condition are apartment/commercial-only → no apt section load
		expect(states.aptAttributes.total).toBe(0);
	});
});

describe("progress + first incomplete section", () => {
	it("total includes the photos pseudo-field and filled grows monotonically", () => {
		const empty = getRequiredProgress(emptyValues(), "create", 0);
		// 11 field errors (see parity test) + type prefilled + photos
		expect(empty.total).toBe(13);
		expect(empty.filled).toBe(1); // `type` is pre-filled by default

		const withPhotos = getRequiredProgress(emptyValues(), "create", 2);
		expect(withPhotos.filled).toBe(2);

		const done = getRequiredProgress(filledApartment(), "create", 2);
		expect(done.filled).toBe(done.total);
	});

	it("totals differ across property types", () => {
		const apt = getRequiredProgress(emptyValues(), "create", 0);
		const land = getRequiredProgress(
			emptyValues({ property_type: "land" }),
			"create",
			0,
		);
		expect(land.total).toBeLessThan(apt.total);
		// photos + type (pre-filled) + price + region + district + map
		expect(land.total).toBe(6);
	});

	it("getFirstIncompleteSection walks the visual order, photos first", () => {
		expect(getFirstIncompleteSection(emptyValues(), "create", 0)).toBe(
			"photos",
		);
		// market_type now lives in the Type section → with photos covered,
		// the first gap on a fresh apartment form is the classifier.
		expect(getFirstIncompleteSection(emptyValues(), "create", 1)).toBe(
			"type",
		);
		expect(
			getFirstIncompleteSection(filledApartment(), "create", 1),
		).toBeNull();
		expect(
			getFirstIncompleteSection(
				filledApartment({ region: "" }),
				"create",
				1,
			),
		).toBe("location");
	});
});
