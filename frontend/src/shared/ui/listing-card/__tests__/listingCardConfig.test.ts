import { describe, it, expect } from "vitest";
import {
	CARD_WORTHY,
	getCardChipFields,
	getCardFields,
	getCardFinanceFields,
	getCardTagFields,
} from "../listingCardConfig";
import { getVisibleFields } from "@modules/seller/feature/listing-form/lib/visibility";

describe("listingCardConfig — derived from visibility matrix", () => {
	describe("getCardFields", () => {
		it("apartment × sell shows rooms/area/floor + finance flags, no rent fields", () => {
			const fields = getCardFields("apartment", "sell");
			expect(fields).toContain("rooms");
			expect(fields).toContain("area");
			expect(fields).toContain("floor");
			expect(fields).toContain("building_type");
			expect(fields).toContain("condition");
			expect(fields).toContain("mortgage_ok");
			expect(fields).toContain("installment_ok");
			expect(fields).toContain("halol_ok");
			expect(fields).not.toContain("rent_period");
			expect(fields).not.toContain("land_area");
			expect(fields).not.toContain("land_purpose");
		});

		it("apartment × rent shows rent_period, no sale-finance flags", () => {
			const fields = getCardFields("apartment", "rent");
			expect(fields).toContain("rent_period");
			expect(fields).toContain("rooms");
			expect(fields).toContain("floor");
			expect(fields).not.toContain("mortgage_ok");
			expect(fields).not.toContain("installment_ok");
			expect(fields).not.toContain("halol_ok");
		});

		it("house × sell includes land_area, excludes floor (hidden in house matrix)", () => {
			const fields = getCardFields("house", "sell");
			expect(fields).toContain("land_area");
			expect(fields).not.toContain("floor");
			expect(fields).not.toContain("building_type"); // apt-only
			expect(fields).not.toContain("condition"); // not visible on house
		});

		it("commercial × sell excludes rooms + land fields", () => {
			const fields = getCardFields("commercial", "sell");
			expect(fields).not.toContain("rooms"); // hidden on commercial
			expect(fields).not.toContain("land_area");
			expect(fields).not.toContain("land_purpose");
			expect(fields).toContain("area");
			expect(fields).toContain("floor");
			expect(fields).toContain("mortgage_ok");
		});

		it("land × sell shows only land_area + land_purpose (+ finance flags)", () => {
			const fields = getCardFields("land", "sell");
			expect(fields).toContain("land_area");
			expect(fields).toContain("land_purpose");
			expect(fields).toContain("mortgage_ok"); // sale flags visible on land×sell
			expect(fields).not.toContain("rooms");
			expect(fields).not.toContain("floor");
			expect(fields).not.toContain("area");
			expect(fields).not.toContain("condition");
			expect(fields).not.toContain("building_type");
		});

		it("land × rent shows land base + rent_period (P3 retired)", () => {
			const landRent = getCardFields("land", "rent");
			expect(landRent).toContain("land_area");
			expect(landRent).toContain("land_purpose");
			expect(landRent).toContain("rent_period");
			expect(landRent).not.toContain("mortgage_ok"); // sale-only
			expect(landRent).not.toContain("rooms");
		});
	});

	describe("chip/tag/finance subset derivation", () => {
		it("getCardChipFields is a subset of visible fields", () => {
			for (const pt of ["apartment", "house", "commercial", "land"] as const) {
				for (const dt of ["sell", "rent"] as const) {
					const visible = new Set(getVisibleFields(pt, dt));
					for (const f of getCardChipFields(pt, dt)) {
						expect(visible.has(f)).toBe(true);
					}
				}
			}
		});

		it("getCardTagFields is a subset of visible fields", () => {
			for (const pt of ["apartment", "house", "commercial", "land"] as const) {
				for (const dt of ["sell", "rent"] as const) {
					const visible = new Set(getVisibleFields(pt, dt));
					for (const f of getCardTagFields(pt, dt)) {
						expect(visible.has(f)).toBe(true);
					}
				}
			}
		});

		it("getCardFinanceFields is empty for rent listings", () => {
			expect(getCardFinanceFields("apartment", "rent")).toEqual([]);
			expect(getCardFinanceFields("house", "rent")).toEqual([]);
			expect(getCardFinanceFields("commercial", "rent")).toEqual([]);
		});

		it("getCardFinanceFields includes all three flags on sell combos", () => {
			for (const pt of ["apartment", "house", "commercial", "land"] as const) {
				const fin = getCardFinanceFields(pt, "sell");
				expect(fin).toContain("mortgage_ok");
				expect(fin).toContain("installment_ok");
				expect(fin).toContain("halol_ok");
			}
		});
	});

	describe("CARD_WORTHY invariants", () => {
		it("contains no duplicates", () => {
			const set = new Set(CARD_WORTHY);
			expect(set.size).toBe(CARD_WORTHY.length);
		});

		it("every CARD_WORTHY field is visible in at least one combo", () => {
			// Proves the set is derived, not fabricated.
			for (const field of CARD_WORTHY) {
				const someComboShows = (
					["apartment", "house", "commercial", "land"] as const
				).some((pt) =>
					(["sell", "rent"] as const).some((dt) =>
						getVisibleFields(pt, dt).includes(field),
					),
				);
				expect(someComboShows).toBe(true);
			}
		});
	});
});
