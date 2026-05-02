// T-020 — ListingCardVariant config layer.
//
// The card displays a subset of fields. That subset is DERIVED from the
// visibility matrix in `visibility.ts` — it is NOT a parallel source of
// truth. The `CARD_WORTHY` constant only lists which VISIBLE fields are
// meaningful for a card (vs. belonging to the full form only). If a field
// is not visible for a combo, it is automatically excluded here too.

import {
	getVisibleFields,
	type DealType,
	type FieldKey,
	type PropertyType,
} from "@modules/seller/feature/listing-form/lib/visibility";

// Subset of FieldKey that the card CAN render. Cards stay compact — they
// don't show every form field. Order here is the display order within each
// section on the card.
//
// Grouping:
//   Dimension chips:  rooms, area, floor, total_floors, land_area
//   Tag line:         building_type, condition, land_purpose
//   Finance badges:   mortgage_ok, installment_ok, halol_ok, deed_type
//   Rent indicator:   rent_period (drives the price period suffix)
export const CARD_WORTHY: readonly FieldKey[] = [
	"rooms",
	"area",
	"floor",
	"total_floors",
	"land_area",
	"building_type",
	"condition",
	"land_purpose",
	"rent_period",
	"mortgage_ok",
	"installment_ok",
	"halol_ok",
];

// Fields rendered in the dimension-chip row of the card.
const CHIP_FIELDS: readonly FieldKey[] = [
	"rooms",
	"area",
	"floor",
	"land_area",
];

// Fields rendered in the single-line tag below the chips.
const TAG_FIELDS: readonly FieldKey[] = [
	"building_type",
	"condition",
	"land_purpose",
];

// Fields surfaced as "sale-finance" badges in the card header.
const FINANCE_FIELDS: readonly FieldKey[] = [
	"mortgage_ok",
	"installment_ok",
	"halol_ok",
];

/**
 * Return the card-displayable fields for a (property_type, deal_type) combo.
 *
 * Derived as CARD_WORTHY ∩ getVisibleFields(pt, dt). The card never renders
 * fields hidden by the matrix, no matter what the data payload contains.
 */
export function getCardFields(
	propertyType: PropertyType,
	dealType: DealType,
): readonly FieldKey[] {
	const visible = new Set(getVisibleFields(propertyType, dealType));
	return CARD_WORTHY.filter((f) => visible.has(f));
}

export function getCardChipFields(
	propertyType: PropertyType,
	dealType: DealType,
): readonly FieldKey[] {
	const visible = new Set(getVisibleFields(propertyType, dealType));
	return CHIP_FIELDS.filter((f) => visible.has(f));
}

export function getCardTagFields(
	propertyType: PropertyType,
	dealType: DealType,
): readonly FieldKey[] {
	const visible = new Set(getVisibleFields(propertyType, dealType));
	return TAG_FIELDS.filter((f) => visible.has(f));
}

export function getCardFinanceFields(
	propertyType: PropertyType,
	dealType: DealType,
): readonly FieldKey[] {
	const visible = new Set(getVisibleFields(propertyType, dealType));
	return FINANCE_FIELDS.filter((f) => visible.has(f));
}
