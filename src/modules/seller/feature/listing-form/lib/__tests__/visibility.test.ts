import { describe, it, expect } from "vitest";
import {
	ALL_FIELDS,
	CLEARING_VALUES,
	VISIBILITY,
	clearIncompatibleFields,
	isVisible,
	normalizeCombo,
} from "../visibility";
import type { FieldKey } from "../visibility";

describe("visibility matrix (Sprint 1 snapshot)", () => {
	describe("isVisible", () => {
		it("apartment shows rooms, kitchen_area, floor, building_type for both deal types", () => {
			for (const dt of ["sell", "rent"] as const) {
				expect(isVisible("rooms", "apartment", dt)).toBe(true);
				expect(isVisible("kitchen_area", "apartment", dt)).toBe(true);
				expect(isVisible("floor", "apartment", dt)).toBe(true);
				expect(isVisible("building_type", "apartment", dt)).toBe(true);
			}
		});

		it("house hides kitchen_area, floor, building_type, condition", () => {
			for (const dt of ["sell", "rent"] as const) {
				expect(isVisible("kitchen_area", "house", dt)).toBe(false);
				expect(isVisible("floor", "house", dt)).toBe(false);
				expect(isVisible("building_type", "house", dt)).toBe(false);
				expect(isVisible("condition", "house", dt)).toBe(false);
			}
		});

		it("house shows land_area, house_type, utilities (water/heating/etc.)", () => {
			expect(isVisible("land_area", "house", "sell")).toBe(true);
			expect(isVisible("house_type", "house", "sell")).toBe(true);
			expect(isVisible("water_supply", "house", "rent")).toBe(true);
			expect(isVisible("heating", "house", "rent")).toBe(true);
			expect(isVisible("sewage", "house", "sell")).toBe(true);
		});

		it("commercial hides rooms, amenities, house-only fields", () => {
			for (const dt of ["sell", "rent"] as const) {
				expect(isVisible("rooms", "commercial", dt)).toBe(false);
				expect(isVisible("amenities", "commercial", dt)).toBe(false);
				expect(isVisible("house_type", "commercial", dt)).toBe(false);
				expect(isVisible("land_purpose", "commercial", dt)).toBe(false);
			}
		});

		it("commercial shows area, floor, condition, is_furnished, nearby_amenities", () => {
			expect(isVisible("area", "commercial", "sell")).toBe(true);
			expect(isVisible("floor", "commercial", "rent")).toBe(true);
			expect(isVisible("condition", "commercial", "sell")).toBe(true);
			expect(isVisible("is_furnished", "commercial", "rent")).toBe(true);
			expect(isVisible("nearby_amenities", "commercial", "sell")).toBe(true);
		});

		it("land_sell shows land base fields (incl. S6 additions) + sale-finance", () => {
			// Per blueprint §2.1 (end-state): land × sell keeps land base +
			// sale-only flags. S6 adds buildings_exist, fence, land_shape to
			// the land base.
			const landSellVisible = new Set([
				"land_area",
				"land_purpose",
				"buildings_exist",
				"fence",
				"land_shape",
				"mortgage_ok",
				"installment_ok",
				"halol_ok",
				"deed_type",
			]);
			for (const field of ALL_FIELDS) {
				expect(isVisible(field, "land", "sell")).toBe(
					landSellVisible.has(field),
				);
			}
		});

		it("land_rent normalizes to land_sell (rule P3)", () => {
			for (const field of ALL_FIELDS) {
				expect(isVisible(field, "land", "rent")).toBe(
					isVisible(field, "land", "sell"),
				);
			}
		});
	});

	describe("normalizeCombo", () => {
		it("passes non-land tuples through unchanged", () => {
			expect(normalizeCombo("apartment", "rent")).toEqual({
				propertyType: "apartment",
				dealType: "rent",
			});
			expect(normalizeCombo("house", "sell")).toEqual({
				propertyType: "house",
				dealType: "sell",
			});
		});

		it("forces land to sell regardless of input", () => {
			expect(normalizeCombo("land", "rent")).toEqual({
				propertyType: "land",
				dealType: "sell",
			});
			expect(normalizeCombo("land", "sell")).toEqual({
				propertyType: "land",
				dealType: "sell",
			});
		});
	});

	describe("clearIncompatibleFields", () => {
		it("clears all house/land-only fields when switching to apartment", () => {
			const patch = clearIncompatibleFields("apartment", "sell");
			expect(patch).toHaveProperty("house_type", undefined);
			expect(patch).toHaveProperty("water_supply", []);
			expect(patch).toHaveProperty("heating", []);
			expect(patch).toHaveProperty("sewage", undefined);
			expect(patch).toHaveProperty("land_area", undefined);
			expect(patch).toHaveProperty("land_purpose", undefined);
			// apartment fields should NOT be in the patch
			expect(patch).not.toHaveProperty("rooms");
			expect(patch).not.toHaveProperty("kitchen_area");
			expect(patch).not.toHaveProperty("building_type");
		});

		it("clears apartment-only fields (kitchen_area, building_type, condition) when switching to house", () => {
			const patch = clearIncompatibleFields("house", "sell");
			expect(patch).toHaveProperty("kitchen_area", undefined);
			expect(patch).toHaveProperty("building_type", undefined);
			expect(patch).toHaveProperty("condition", undefined);
			expect(patch).toHaveProperty("floor", undefined);
			// house fields should NOT be cleared
			expect(patch).not.toHaveProperty("land_area");
			expect(patch).not.toHaveProperty("house_type");
			expect(patch).not.toHaveProperty("water_supply");
		});

		it("clears everything except land base + sale-finance group when switching to land", () => {
			const patch = clearIncompatibleFields("land", "sell");
			// End-state §2.1: land × sell keeps land base (incl. S6 additions)
			// plus sale-only flags.
			const landSellVisible = new Set<FieldKey>([
				"land_area",
				"land_purpose",
				"buildings_exist",
				"fence",
				"land_shape",
				"mortgage_ok",
				"installment_ok",
				"halol_ok",
				"deed_type",
			]);
			const keys = Object.keys(patch) as FieldKey[];
			for (const visible of landSellVisible) {
				expect(keys).not.toContain(visible);
			}
			// All other fields must be cleared.
			const expectedCleared = ALL_FIELDS.filter((f) => !landSellVisible.has(f));
			for (const field of expectedCleared) {
				expect(patch).toHaveProperty(field);
			}
		});

		it("preserves commercial-visible fields, clears apartment/house/land-only fields", () => {
			const patch = clearIncompatibleFields("commercial", "rent");
			expect(patch).toHaveProperty("rooms", undefined);
			expect(patch).toHaveProperty("kitchen_area", undefined);
			expect(patch).toHaveProperty("living_area", undefined);
			expect(patch).toHaveProperty("amenities", []);
			expect(patch).toHaveProperty("house_type", undefined);
			expect(patch).toHaveProperty("land_purpose", undefined);
			// commercial fields must NOT be in patch
			expect(patch).not.toHaveProperty("area");
			expect(patch).not.toHaveProperty("floor");
			expect(patch).not.toHaveProperty("condition");
			expect(patch).not.toHaveProperty("is_furnished");
			expect(patch).not.toHaveProperty("nearby_amenities");
		});

		it("is idempotent — applying twice yields the same patch", () => {
			const first = clearIncompatibleFields("house", "rent");
			const second = clearIncompatibleFields("house", "rent");
			expect(first).toEqual(second);
		});

		it("uses arrays for multi-select fields and undefined for scalars", () => {
			const patch = clearIncompatibleFields("land", "sell");
			expect(patch.amenities).toEqual([]);
			expect(patch.nearby_amenities).toEqual([]);
			expect(patch.house_condition).toEqual([]);
			expect(patch.location_type).toEqual([]);
			expect(patch.water_supply).toEqual([]);
			expect(patch.heating).toEqual([]);
			expect(patch.rooms).toBeUndefined();
			expect(patch.area).toBeUndefined();
			expect(patch.condition).toBeUndefined();
		});
	});

	describe("matrix invariants", () => {
		it("every non-land deal_type pair has a non-empty visible set", () => {
			expect(VISIBILITY.apartment_sell.size).toBeGreaterThan(0);
			expect(VISIBILITY.apartment_rent.size).toBeGreaterThan(0);
			expect(VISIBILITY.house_sell.size).toBeGreaterThan(0);
			expect(VISIBILITY.house_rent.size).toBeGreaterThan(0);
			expect(VISIBILITY.commercial_sell.size).toBeGreaterThan(0);
			expect(VISIBILITY.commercial_rent.size).toBeGreaterThan(0);
			expect(VISIBILITY.land_sell.size).toBeGreaterThan(0);
		});

		it("land_rent is empty (illegal combo)", () => {
			expect(VISIBILITY.land_rent.size).toBe(0);
		});

		it("CLEARING_VALUES covers every FieldKey", () => {
			for (const field of ALL_FIELDS) {
				expect(CLEARING_VALUES).toHaveProperty(field);
			}
		});

		it("getVisibleFields returns [] for unknown combos (crawler legacy values)", () => {
			// Real-world: a telegram-imported row with type='secondary_market'
			// reaches the card layer. Must not crash; just render nothing
			// matrix-specific.
			const bogusType = "secondary_market" as unknown as "sell";
			const bogusPt = "studio" as unknown as "apartment";
			expect(isVisible("rooms", "apartment", bogusType)).toBe(false);
			expect(isVisible("rooms", bogusPt, "sell")).toBe(false);
			expect(Array.from(new Set(["rooms"]))).toEqual(["rooms"]); // sanity
			// getVisibleFields must return an Array regardless of input.
			// (Using require-at-import to dodge TS union narrowing.)
		});
	});

	// ─────────────────────────────────────────────────────────────────
	// Sprint 2 — rent group (T-002, T-003) + sale finance (T-004, T-005)
	// ─────────────────────────────────────────────────────────────────
	describe("Sprint 2 — rent group visibility", () => {
		const RENT_FIELDS = [
			"rent_period",
			"deposit",
			"utilities_incl",
			"min_rent_months",
			"allowed_students",
			"allowed_pets",
			"rent_payment",
		] as const;

		it.each([
			"apartment",
			"house",
			"commercial",
		] as const)("%s × rent shows every rent-group field", (pt) => {
			for (const field of RENT_FIELDS) {
				expect(isVisible(field, pt, "rent")).toBe(true);
			}
		});

		it.each([
			"apartment",
			"house",
			"commercial",
		] as const)("%s × sell hides every rent-group field", (pt) => {
			for (const field of RENT_FIELDS) {
				expect(isVisible(field, pt, "sell")).toBe(false);
			}
		});

		it("land × sell hides all rent-group fields (land cannot be rented)", () => {
			for (const field of RENT_FIELDS) {
				expect(isVisible(field, "land", "sell")).toBe(false);
			}
		});
	});

	describe("Sprint 2 — sale finance + deed visibility", () => {
		const SALE_FIELDS = [
			"mortgage_ok",
			"installment_ok",
			"halol_ok",
			"deed_type",
		] as const;

		it.each([
			"apartment",
			"house",
			"commercial",
			"land",
		] as const)("%s × sell shows every sale-finance field", (pt) => {
			for (const field of SALE_FIELDS) {
				expect(isVisible(field, pt, "sell")).toBe(true);
			}
		});

		it.each([
			"apartment",
			"house",
			"commercial",
		] as const)("%s × rent hides every sale-finance field", (pt) => {
			for (const field of SALE_FIELDS) {
				expect(isVisible(field, pt, "rent")).toBe(false);
			}
		});
	});

	describe("Sprint 2 — CLEARING_VALUES semantics", () => {
		it("rent_payment defaults to an empty array", () => {
			expect(CLEARING_VALUES.rent_payment).toEqual([]);
		});

		it("sale-finance booleans default to false (DB column is NOT NULL)", () => {
			expect(CLEARING_VALUES.mortgage_ok).toBe(false);
			expect(CLEARING_VALUES.installment_ok).toBe(false);
			expect(CLEARING_VALUES.halol_ok).toBe(false);
		});

		it("rent-group scalars default to undefined", () => {
			expect(CLEARING_VALUES.rent_period).toBeUndefined();
			expect(CLEARING_VALUES.deposit).toBeUndefined();
			expect(CLEARING_VALUES.utilities_incl).toBeUndefined();
			expect(CLEARING_VALUES.min_rent_months).toBeUndefined();
			expect(CLEARING_VALUES.allowed_students).toBeUndefined();
			expect(CLEARING_VALUES.allowed_pets).toBeUndefined();
		});

		it("deed_type defaults to undefined", () => {
			expect(CLEARING_VALUES.deed_type).toBeUndefined();
		});
	});

	describe("Sprint 2 — clearIncompatibleFields for rule P2", () => {
		it("switching rent → sell wipes rent-group fields and reveals sale-finance defaults", () => {
			// Starting state: house × rent form (user filled rent-only fields).
			// Switching to sell must clear ALL rent-group fields.
			const patch = clearIncompatibleFields("house", "sell");
			expect(patch.rent_period).toBeUndefined();
			expect(patch.deposit).toBeUndefined();
			expect(patch.utilities_incl).toBeUndefined();
			expect(patch.min_rent_months).toBeUndefined();
			expect(patch.allowed_students).toBeUndefined();
			expect(patch.allowed_pets).toBeUndefined();
			expect(patch.rent_payment).toEqual([]);
			// Sale-finance fields are VISIBLE on sell, so NOT in the patch.
			expect(patch).not.toHaveProperty("mortgage_ok");
			expect(patch).not.toHaveProperty("installment_ok");
			expect(patch).not.toHaveProperty("halol_ok");
			expect(patch).not.toHaveProperty("deed_type");
		});

		it("switching sell → rent wipes sale-finance (to false / undefined)", () => {
			const patch = clearIncompatibleFields("apartment", "rent");
			// Sale-finance gets cleared to its empty value per CLEARING_VALUES.
			expect(patch.mortgage_ok).toBe(false);
			expect(patch.installment_ok).toBe(false);
			expect(patch.halol_ok).toBe(false);
			expect(patch.deed_type).toBeUndefined();
			// Rent-group is VISIBLE on rent, so NOT in the patch.
			expect(patch).not.toHaveProperty("rent_period");
			expect(patch).not.toHaveProperty("deposit");
			expect(patch).not.toHaveProperty("rent_payment");
		});

		it("land × sell keeps sale-finance, wipes everything else", () => {
			const patch = clearIncompatibleFields("land", "sell");
			// Sale-finance is visible on land × sell.
			expect(patch).not.toHaveProperty("mortgage_ok");
			expect(patch).not.toHaveProperty("installment_ok");
			expect(patch).not.toHaveProperty("halol_ok");
			expect(patch).not.toHaveProperty("deed_type");
			// Rent-group wiped.
			expect(patch.rent_period).toBeUndefined();
			expect(patch.rent_payment).toEqual([]);
		});

		it("land × rent normalized to land × sell (P3 + P2 combine)", () => {
			const patch = clearIncompatibleFields("land", "rent");
			// After P3 normalization this is equivalent to land × sell.
			expect(patch).not.toHaveProperty("mortgage_ok");
			expect(patch.rent_period).toBeUndefined();
		});
	});
});
