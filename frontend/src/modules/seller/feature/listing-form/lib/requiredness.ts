/**
 * Single source of truth for required-field rules on the listing form.
 *
 * Before this module the same knowledge lived in three diverging places:
 * the inline `validate` rules in useListingForm, the `required` props in
 * ListingFormFields JSX, and the `hasMinimumParams` gate in Stage1. The
 * Mantine validate object is now GENERATED from this table
 * (buildValidateRules), and the section-status / progress UI reads the
 * very same predicates, so they cannot drift apart again.
 *
 * Falsy semantics are preserved exactly from the original validate rules:
 * `!value` for price/area/region/…, `=== undefined` for numeric fields
 * where 0 would be a valid value (rooms, floor, total_floors,
 * min_rent_months).
 */

import type {
	ListingFormValues,
	ListingFormMode,
} from "../ui/useListingForm";

export type RequiredFieldKey =
	| "type"
	| "price"
	| "rooms"
	| "area"
	| "floor"
	| "total_floors"
	| "market_type"
	| "condition"
	| "furniture"
	| "commercial_type"
	| "rent_period"
	| "min_rent_months"
	| "region"
	| "district"
	| "latitude";

export interface RequiredRule {
	requiredWhen: (values: ListingFormValues, mode: ListingFormMode) => boolean;
	isFilled: (values: ListingFormValues) => boolean;
	/** i18n key in the `seller` namespace — same keys the old validate used. */
	errorKey: string;
}

export const REQUIRED_RULES: Record<RequiredFieldKey, RequiredRule> = {
	type: {
		requiredWhen: (v) => v.property_type !== "land",
		isFilled: (v) => !!v.type,
		errorKey: "validation.dealTypeRequired",
	},
	price: {
		requiredWhen: (v) => !v.is_negotiable,
		isFilled: (v) => v.price != null && v.price > 0,
		errorKey: "validation.priceRequired",
	},
	rooms: {
		requiredWhen: (v) =>
			(v.property_type === "apartment" || v.property_type === "house") &&
			v.listing_subtype !== "studio",
		isFilled: (v) => v.rooms !== undefined,
		errorKey: "validation.roomsRequired",
	},
	area: {
		requiredWhen: (v) => v.property_type !== "land",
		isFilled: (v) => !!v.area,
		errorKey: "validation.areaRequired",
	},
	floor: {
		requiredWhen: (v) =>
			v.property_type === "apartment" || v.property_type === "commercial",
		isFilled: (v) => v.floor !== undefined,
		errorKey: "validation.floorRequired",
	},
	total_floors: {
		requiredWhen: (v) =>
			v.property_type === "apartment" ||
			v.property_type === "commercial" ||
			v.property_type === "house",
		isFilled: (v) => v.total_floors !== undefined,
		errorKey: "validation.totalFloorsRequired",
	},
	// S5 dual-read: market_type replaces building_type as the required
	// apartment-only field; the legacy error key is kept on purpose.
	market_type: {
		requiredWhen: (v) => v.property_type === "apartment",
		isFilled: (v) => !!v.market_type,
		errorKey: "validation.buildingTypeRequired",
	},
	condition: {
		requiredWhen: (v) =>
			v.property_type === "apartment" || v.property_type === "commercial",
		isFilled: (v) => !!v.condition,
		errorKey: "validation.conditionRequired",
	},
	// S5 dual-read: furniture replaces is_furnished.
	furniture: {
		requiredWhen: (v) => v.property_type !== "land",
		isFilled: (v) => !!v.furniture,
		errorKey: "validation.furnishedRequired",
	},
	// S4 (T-009): commercial listings require commercial_type on CREATE only.
	commercial_type: {
		requiredWhen: (v, mode) =>
			mode === "create" && v.property_type === "commercial",
		isFilled: (v) => !!v.commercial_type,
		errorKey: "validation.commercialTypeRequired",
	},
	// Sprint 2 — rent listings require a period (blueprint §3.3)
	rent_period: {
		requiredWhen: (v) => v.type === "rent" && v.property_type !== "land",
		isFilled: (v) => !!v.rent_period,
		errorKey: "validation.rentPeriodRequired",
	},
	// Long-term rentals additionally require min_rent_months
	min_rent_months: {
		requiredWhen: (v) =>
			v.type === "rent" &&
			v.property_type !== "land" &&
			v.rent_period === "long_term",
		isFilled: (v) => v.min_rent_months !== undefined,
		errorKey: "validation.minRentMonthsRequired",
	},
	region: {
		requiredWhen: () => true,
		isFilled: (v) => !!v.region,
		errorKey: "validation.regionRequired",
	},
	district: {
		requiredWhen: () => true,
		isFilled: (v) => !!v.district,
		errorKey: "validation.districtRequired",
	},
	latitude: {
		requiredWhen: () => true,
		isFilled: (v) => !!v.latitude,
		errorKey: "validation.mapRequired",
	},
};

const REQUIRED_FIELD_KEYS = Object.keys(REQUIRED_RULES) as RequiredFieldKey[];

// ── Section model ──
// Keys mirror the FormSection blocks as rendered: `photos` lives in the
// pages (Stage1 / edit Page), the rest inside ListingFormFields.

export type SectionKey =
	| "photos"
	| "type"
	| "parameters"
	| "aptAttributes"
	| "houseAttributes"
	| "utilities"
	| "landPurpose"
	| "commercial"
	| "amenities"
	| "location"
	| "description"
	| "price"
	| "contact";

/** Visual order of sections on both pages — drives scroll-to-first-incomplete. */
export const SECTION_ORDER: readonly SectionKey[] = [
	"photos",
	"type",
	"parameters",
	"aptAttributes",
	"houseAttributes",
	"utilities",
	"landPurpose",
	"commercial",
	"amenities",
	"location",
	"description",
	"price",
	"contact",
];

/**
 * Which section a required field is rendered in. `furniture` is the only
 * dynamic assignment: it renders inside "House attributes" for houses and
 * inside "Apartment attributes" for apartment/commercial.
 */
export function fieldSection(
	field: RequiredFieldKey,
	values: ListingFormValues,
): SectionKey {
	switch (field) {
		case "type":
			return "type";
		case "rooms":
		case "area":
		case "floor":
		case "total_floors":
			return "parameters";
		case "market_type":
		case "condition":
			return "aptAttributes";
		case "furniture":
			return values.property_type === "house"
				? "houseAttributes"
				: "aptAttributes";
		case "commercial_type":
			return "commercial";
		case "region":
		case "district":
		case "latitude":
			return "location";
		case "price":
		case "rent_period":
		case "min_rent_months":
			return "price";
	}
}

export type SectionStatus = "neutral" | "complete" | "error";

export interface SectionState {
	status: SectionStatus;
	/** Unfilled required fields in this section. */
	remaining: number;
	/** Required fields in this section under the current combo (0 → always neutral). */
	total: number;
}

interface SectionCounters {
	remaining: number;
	total: number;
}

function collectSectionCounters(
	values: ListingFormValues,
	mode: ListingFormMode,
	imageCount: number,
): Record<SectionKey, SectionCounters> {
	const counters = {} as Record<SectionKey, SectionCounters>;
	for (const key of SECTION_ORDER) {
		counters[key] = { remaining: 0, total: 0 };
	}
	// Photos pseudo-field — owned by the pages, not by the form values.
	counters.photos.total = 1;
	if (imageCount === 0) counters.photos.remaining = 1;

	for (const field of REQUIRED_FIELD_KEYS) {
		const rule = REQUIRED_RULES[field];
		if (!rule.requiredWhen(values, mode)) continue;
		const section = counters[fieldSection(field, values)];
		section.total += 1;
		if (!rule.isFilled(values)) section.remaining += 1;
	}
	return counters;
}

/**
 * Section statuses for the bordered-card UI.
 * - total === 0 → "neutral" (section has no required fields → never colored)
 * - remaining === 0 → "complete" (live, regardless of submitAttempted)
 * - remaining > 0 → "error" only after the first failed submit attempt
 */
export function getSectionStates(
	values: ListingFormValues,
	mode: ListingFormMode,
	imageCount: number,
	submitAttempted: boolean,
): Record<SectionKey, SectionState> {
	const counters = collectSectionCounters(values, mode, imageCount);
	const states = {} as Record<SectionKey, SectionState>;
	for (const key of SECTION_ORDER) {
		const { remaining, total } = counters[key];
		let status: SectionStatus = "neutral";
		if (total > 0) {
			if (remaining === 0) status = "complete";
			else if (submitAttempted) status = "error";
		}
		states[key] = { status, remaining, total };
	}
	return states;
}

/** Overall required-field progress (includes the photos pseudo-field). */
export function getRequiredProgress(
	values: ListingFormValues,
	mode: ListingFormMode,
	imageCount: number,
): { filled: number; total: number } {
	const counters = collectSectionCounters(values, mode, imageCount);
	let filled = 0;
	let total = 0;
	for (const key of SECTION_ORDER) {
		total += counters[key].total;
		filled += counters[key].total - counters[key].remaining;
	}
	return { filled, total };
}

/** First section (in visual order) that still has unfilled required fields. */
export function getFirstIncompleteSection(
	values: ListingFormValues,
	mode: ListingFormMode,
	imageCount: number,
): SectionKey | null {
	const counters = collectSectionCounters(values, mode, imageCount);
	for (const key of SECTION_ORDER) {
		if (counters[key].remaining > 0) return key;
	}
	return null;
}

type ValidateRule = (
	value: unknown,
	values: ListingFormValues,
) => string | null;

/**
 * Generates the Mantine `validate` object from REQUIRED_RULES so the form
 * validation and the section-status UI share one definition of "required".
 * Error messages use the exact same i18n keys as the old inline rules.
 */
export function buildValidateRules(
	mode: ListingFormMode,
	t: (key: string) => string,
): Partial<Record<RequiredFieldKey, ValidateRule>> {
	const rules: Partial<Record<RequiredFieldKey, ValidateRule>> = {};
	for (const field of REQUIRED_FIELD_KEYS) {
		const rule = REQUIRED_RULES[field];
		rules[field] = (_value, values) =>
			rule.requiredWhen(values, mode) && !rule.isFilled(values)
				? t(rule.errorKey)
				: null;
	}
	return rules;
}
