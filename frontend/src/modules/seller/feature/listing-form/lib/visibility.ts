// Central visibility matrix for the listing form (T-031, Sprint 1 + Sprint 2).
//
// Single source of truth for (property_type × deal_type) → visible fields.
// Sprint 2 adds 11 fields split into sale-only and rent-only groups.
// Backend mirror lives in backend/app/api/v1/listings.py::_VISIBILITY_MATRIX.
// A parity test (backend/tests/unit/test_matrix_parity.py) guards drift.

export type PropertyType = "apartment" | "house" | "commercial" | "land";
export type DealType = "sell" | "rent";

// Only fields whose visibility depends on (property_type, deal_type).
// Always-visible fields (title, description, price, currency, is_negotiable,
// region, district, address, latitude, longitude, phone, seller_type) are not
// part of this union.
export type FieldKey =
	// Sprint 1 — property-type fields
	| "rooms"
	| "area"
	| "living_area"
	| "kitchen_area"
	| "land_area"
	| "floor"
	| "total_floors"
	| "building_type"
	| "condition"
	| "house_type"
	| "house_condition"
	| "location_type"
	| "water_supply"
	| "electricity"
	| "heating"
	| "gas_supply"
	| "sewage"
	| "is_furnished"
	| "land_purpose"
	| "amenities"
	| "nearby_amenities"
	// Sprint 2 — rent group (T-002, T-003)
	| "rent_period"
	| "deposit"
	| "utilities_incl"
	| "min_rent_months"
	| "allowed_students"
	| "allowed_pets"
	| "rent_payment"
	// Sprint 2 — sale finance + deed (T-004, T-005)
	| "mortgage_ok"
	| "installment_ok"
	| "halol_ok"
	| "deed_type"
	// Sprint 3 — cross-cutting location (T-001) — `jk_name`, `metro_station`
	// are matrix-gated; the rest (city, microdistrict, landmark,
	// seller_telegram, urgent_flag) are always-visible per §2.1 header
	// note and not enumerated here.
	| "jk_name"
	| "metro_station"
	// Sprint 4 — commercial-only (T-009)
	| "commercial_type"
	| "price_per_sqm"
	| "ceiling_height"
	| "entrance"
	| "parking_comm"
	| "building_class"
	// Sprint 5 — dual-read renames (T-006, T-008)
	| "market_type"
	| "wall_material"
	| "furniture"
	// Sprint 6 — property polish (T-011, T-014, T-015)
	| "garage"
	| "basement"
	| "buildings_exist"
	| "fence"
	| "land_shape"
	| "balcony"
	| "listing_subtype"
	| "floor_plan_url";

type Combo = `${PropertyType}_${DealType}`;

// ── Sale/rent field groups (Sprint 2, blueprint §2.2 P2) ──
const SALE_ONLY_FIELDS: readonly FieldKey[] = [
	"mortgage_ok",
	"installment_ok",
	"halol_ok",
	"deed_type",
];

const RENT_ONLY_FIELDS: readonly FieldKey[] = [
	"rent_period",
	"deposit",
	"utilities_incl",
	"min_rent_months",
	"allowed_students",
	"allowed_pets",
	"rent_payment",
];

// ── Property-type base field sets — end-state per blueprint §2.1 ──
// Sprint-3 additions (jk_name, metro_station) attach to the property types
// allowed by the matrix. Sprint-5 additions (market_type, wall_material,
// furniture) replace building_type / is_furnished in the matrix while the
// old names remain in the type union (dual-read window). Sprint-6 polish
// fields are property-type-scoped per §2.1.
const APARTMENT_BASE_FIELDS: readonly FieldKey[] = [
	"rooms",
	"area",
	"living_area",
	"kitchen_area",
	"floor",
	"total_floors",
	"ceiling_height", // optional, all types except land
	"building_type", // S5: kept during dual-read window
	"market_type", // S5: new
	"wall_material", // S5: new (apartment + house)
	"condition",
	"is_furnished", // S5: kept during dual-read window
	"furniture", // S5: new
	"amenities",
	"nearby_amenities",
	"jk_name", // S3
	"metro_station", // S3 (sub-gated by region)
	"balcony", // S6
	"listing_subtype", // S6
	"floor_plan_url", // S6
];

const HOUSE_BASE_FIELDS: readonly FieldKey[] = [
	"rooms",
	"area",
	"living_area",
	"land_area",
	"total_floors",
	"ceiling_height", // optional, all types except land
	"house_type",
	"house_condition",
	"location_type",
	"water_supply",
	"electricity",
	"heating",
	"gas_supply",
	"sewage",
	"is_furnished", // S5: dual-read
	"furniture", // S5
	"wall_material", // S5
	"amenities",
	"nearby_amenities",
	"garage", // S6
	"basement", // S6
];

const COMMERCIAL_BASE_FIELDS: readonly FieldKey[] = [
	"area",
	"floor",
	"total_floors",
	"condition",
	"is_furnished", // S5: dual-read
	"furniture", // S5
	"nearby_amenities",
	"metro_station", // S3
	"commercial_type", // S4
	"ceiling_height", // S4
	"entrance", // S4
	"parking_comm", // S4
	"building_class", // S4
];

const LAND_BASE_FIELDS: readonly FieldKey[] = [
	"land_area",
	"land_purpose",
	"buildings_exist", // S6
	"fence", // S6
	"land_shape", // S6
];

// Sprint 2 matrix: base ∪ (sale or rent) per deal_type.
// land_rent is illegal (rule P3 coerces type → sell) and empty by construction.
export const VISIBILITY: Record<Combo, ReadonlySet<FieldKey>> = {
	apartment_sell: new Set([...APARTMENT_BASE_FIELDS, ...SALE_ONLY_FIELDS]),
	apartment_rent: new Set([...APARTMENT_BASE_FIELDS, ...RENT_ONLY_FIELDS]),
	house_sell: new Set([...HOUSE_BASE_FIELDS, ...SALE_ONLY_FIELDS]),
	house_rent: new Set([...HOUSE_BASE_FIELDS, ...RENT_ONLY_FIELDS]),
	commercial_sell: new Set([...COMMERCIAL_BASE_FIELDS, ...SALE_ONLY_FIELDS]),
	commercial_rent: new Set([...COMMERCIAL_BASE_FIELDS, ...RENT_ONLY_FIELDS]),
	land_sell: new Set([...LAND_BASE_FIELDS, ...SALE_ONLY_FIELDS]),
	land_rent: new Set<FieldKey>(),
};

// Canonical empty value per field, used to wipe invisible fields.
//   Arrays → []
//   Scalars (enum strings, numbers, nullable booleans) → undefined
//   Non-null sale-finance booleans → false (DB column is NOT NULL with default)
// Mirrors backend _CLEARING_VALUES exactly.
export const CLEARING_VALUES: Record<FieldKey, unknown> = {
	// Sprint 1
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
	// Sprint 2 — rent group
	rent_period: undefined,
	deposit: undefined,
	utilities_incl: undefined,
	min_rent_months: undefined,
	allowed_students: undefined,
	allowed_pets: undefined,
	rent_payment: [],
	// Sprint 2 — sale finance + deed
	mortgage_ok: false,
	installment_ok: false,
	halol_ok: false,
	deed_type: undefined,
	// Sprint 3
	jk_name: undefined,
	metro_station: undefined,
	// Sprint 4
	commercial_type: undefined,
	price_per_sqm: undefined,
	ceiling_height: undefined,
	entrance: undefined,
	parking_comm: undefined,
	building_class: undefined,
	// Sprint 5 — dual-read
	market_type: undefined,
	wall_material: undefined,
	furniture: undefined,
	// Sprint 6
	garage: undefined,
	basement: undefined,
	buildings_exist: undefined,
	fence: undefined,
	land_shape: undefined,
	balcony: undefined,
	listing_subtype: undefined,
	floor_plan_url: undefined,
};

export const ALL_FIELDS: readonly FieldKey[] = Object.keys(
	CLEARING_VALUES,
) as FieldKey[];

export function normalizeCombo(
	propertyType: PropertyType,
	dealType: DealType,
): { propertyType: PropertyType; dealType: DealType } {
	return { propertyType, dealType };
}

// Runtime-safe VISIBILITY lookup. The union types narrow at compile time,
// but crawler-imported rows (telegram / OLX) can carry legacy values like
// `type='secondary_market'` that don't match the union. Returning a safe
// empty fallback beats crashing the whole page.
function _comboAllowlist(
	propertyType: PropertyType,
	dealType: DealType,
): ReadonlySet<FieldKey> {
	const norm = normalizeCombo(propertyType, dealType);
	const combo = `${norm.propertyType}_${norm.dealType}` as Combo;
	return VISIBILITY[combo] ?? new Set<FieldKey>();
}

export function isVisible(
	field: FieldKey,
	propertyType: PropertyType,
	dealType: DealType,
): boolean {
	return _comboAllowlist(propertyType, dealType).has(field);
}

// T-020 helper: return the full allowlist for a (pt, dt) combo as an array,
// preserving the insertion order from the underlying field groups. Used by
// `listingCardConfig.ts` to derive card-displayable fields WITHOUT
// introducing any parallel visibility source.
//
// Returns `[]` for unknown combos rather than throwing — the card layer
// must degrade gracefully when it hits a legacy / crawler row.
export function getVisibleFields(
	propertyType: PropertyType,
	dealType: DealType,
): readonly FieldKey[] {
	return Array.from(_comboAllowlist(propertyType, dealType));
}

// Return a partial form patch that sets every invisible field to its empty
// value for the target (property_type, deal_type). Idempotent: applying it
// twice yields the same result.
export function clearIncompatibleFields(
	propertyType: PropertyType,
	dealType: DealType,
): Partial<Record<FieldKey, unknown>> {
	const patch: Partial<Record<FieldKey, unknown>> = {};
	for (const field of ALL_FIELDS) {
		if (!isVisible(field, propertyType, dealType)) {
			patch[field] = CLEARING_VALUES[field];
		}
	}
	return patch;
}
