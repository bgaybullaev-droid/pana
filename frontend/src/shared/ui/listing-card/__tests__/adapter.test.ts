import { describe, it, expect } from "vitest";
import { getListingCardContent } from "../adapter";
import type { ListingListItem } from "@shared/api/types";

// Minimal TFunction stub. The adapter only calls it for static enum labels,
// fallback text, and i18n keys — we return the key so tests can assert on
// the routing behavior without pulling in i18next.
const t = ((key: string, fallback?: string) =>
	fallback ?? key) as unknown as Parameters<typeof getListingCardContent>[1];

function listing(partial: Partial<ListingListItem>): ListingListItem {
	return {
		id: "id",
		type: "sell",
		property_type: "apartment",
		rooms: null,
		area: null,
		floor: null,
		total_floors: null,
		region: null,
		district: null,
		building_type: null,
		condition: null,
		land_purpose: null,
		price: 50000,
		currency: "USD",
		title: null,
		views_count: 0,
		favorites_count: 0,
		comments_count: 0,
		is_boosted: false,
		is_highlighted: false,
		created_at: "2026-04-14T00:00:00Z",
		primary_image_url: null,
		...partial,
	};
}

describe("getListingCardContent", () => {
	describe("period derivation (matrix-driven, NOT type-based)", () => {
		it("sell listing → period=total", () => {
			const c = getListingCardContent(
				listing({ type: "sell", property_type: "apartment" }),
				t,
			);
			expect(c.price.period).toBe("total");
		});

		it("apartment × rent × long_term → period=month", () => {
			const c = getListingCardContent(
				listing({
					type: "rent",
					property_type: "apartment",
					rent_period: "long_term",
				}),
				t,
			);
			expect(c.price.period).toBe("month");
		});

		it("apartment × rent × daily → period=day", () => {
			const c = getListingCardContent(
				listing({
					type: "rent",
					property_type: "apartment",
					rent_period: "daily",
				}),
				t,
			);
			expect(c.price.period).toBe("day");
		});

		it("apartment × rent with null rent_period defaults to month", () => {
			const c = getListingCardContent(
				listing({
					type: "rent",
					property_type: "apartment",
					rent_period: null,
				}),
				t,
			);
			expect(c.price.period).toBe("month");
		});

		it("land × rent normalizes to land × sell (period=total)", () => {
			// Rule P3: land forces sell.
			const c = getListingCardContent(
				listing({ type: "rent", property_type: "land", rent_period: "daily" }),
				t,
			);
			expect(c.price.period).toBe("total");
		});
	});

	describe("chips — matrix-gated, null-filtered", () => {
		it("apartment chips include rooms/area/floor when present", () => {
			const c = getListingCardContent(
				listing({
					property_type: "apartment",
					rooms: 2,
					area: 55,
					floor: 3,
					total_floors: 9,
				}),
				t,
			);
			const keys = c.chips.map((x) => x.key);
			expect(keys).toContain("rooms");
			expect(keys).toContain("area");
			expect(keys).toContain("floor");
		});

		it("null data fields are dropped (no '-' or 'N/A' placeholder)", () => {
			const c = getListingCardContent(
				listing({
					property_type: "apartment",
					rooms: null,
					area: 55,
					floor: null,
				}),
				t,
			);
			const keys = c.chips.map((x) => x.key);
			expect(keys).toContain("area");
			expect(keys).not.toContain("rooms");
			expect(keys).not.toContain("floor");
		});

		it("commercial omits rooms even if data is present (matrix-gated)", () => {
			const c = getListingCardContent(
				listing({
					property_type: "commercial",
					rooms: 5,
					area: 200,
					floor: 2,
				}),
				t,
			);
			const keys = c.chips.map((x) => x.key);
			expect(keys).not.toContain("rooms");
			expect(keys).toContain("area");
			expect(keys).toContain("floor");
		});

		it("house shows land_area chip (visible per matrix)", () => {
			const c = getListingCardContent(
				listing({
					property_type: "house",
					rooms: 4,
					area: 180,
					land_area: 8,
				}),
				t,
			);
			const keys = c.chips.map((x) => x.key);
			expect(keys).toContain("land_area");
		});

		it("land × sell shows only land_area chip from the chip group", () => {
			const c = getListingCardContent(
				listing({
					property_type: "land",
					type: "sell",
					rooms: 3, // stale data — must be ignored
					area: 100,
					floor: 1,
					land_area: 10,
				}),
				t,
			);
			const keys = c.chips.map((x) => x.key);
			expect(keys).toEqual(["land_area"]);
		});
	});

	describe("finance badges", () => {
		it("sell listing with mortgage_ok=true emits one finance badge", () => {
			const c = getListingCardContent(
				listing({ type: "sell", mortgage_ok: true }),
				t,
			);
			const keys = c.financeBadges.map((b) => b.key);
			expect(keys).toEqual(["mortgage_ok"]);
		});

		it("sell listing with all three flags → three badges", () => {
			const c = getListingCardContent(
				listing({
					type: "sell",
					mortgage_ok: true,
					installment_ok: true,
					halol_ok: true,
				}),
				t,
			);
			const keys = c.financeBadges.map((b) => b.key);
			expect(keys).toEqual(["mortgage_ok", "installment_ok", "halol_ok"]);
		});

		it("rent listing hides sale-finance badges even if flags are true (matrix-gated)", () => {
			const c = getListingCardContent(
				listing({
					type: "rent",
					property_type: "apartment",
					rent_period: "long_term",
					mortgage_ok: true,
					halol_ok: true,
				}),
				t,
			);
			expect(c.financeBadges).toEqual([]);
		});

		it("finance badges skip flags that are false", () => {
			const c = getListingCardContent(
				listing({
					type: "sell",
					mortgage_ok: true,
					installment_ok: false,
					halol_ok: false,
				}),
				t,
			);
			const keys = c.financeBadges.map((b) => b.key);
			expect(keys).toEqual(["mortgage_ok"]);
		});
	});

	describe("tagLine", () => {
		it("apartment: building_type + condition → combined tag", () => {
			const c = getListingCardContent(
				listing({
					property_type: "apartment",
					building_type: "new",
					condition: "euro",
				}),
				t,
			);
			// The stub returns the fallback/label. Comma-joined two labels.
			expect(c.tagLine).toBeTruthy();
			expect(c.tagLine?.includes(",")).toBe(true);
		});

		it("unknown building_type value is skipped", () => {
			const c = getListingCardContent(
				listing({
					property_type: "apartment",
					building_type: "bogus_value_from_crawler",
					condition: null,
				}),
				t,
			);
			expect(c.tagLine).toBeNull();
		});

		it("house hides condition (not in house matrix)", () => {
			const c = getListingCardContent(
				listing({
					property_type: "house",
					condition: "euro",
				}),
				t,
			);
			expect(c.tagLine).toBeNull();
		});

		it("land shows land_purpose tag only", () => {
			const c = getListingCardContent(
				listing({
					property_type: "land",
					type: "sell",
					land_purpose: "private",
					building_type: "new", // must be ignored on land
					condition: "euro", // must be ignored on land
				}),
				t,
			);
			expect(c.tagLine).toBe("listing.landPurpose.private");
		});
	});

	// ────────────────────────────────────────────────────────────────
	// PR6 — T-021: status badges (verified, urgent)
	// ────────────────────────────────────────────────────────────────
	describe("badges (T-021) — adapter is the only place computing them", () => {
		it("verified=true alone emits a single 'verified' badge", () => {
			const c = getListingCardContent(listing({ is_verified: true }), t);
			expect(c.badges).toEqual([{ type: "verified", label: "Проверенный" }]);
		});

		it("urgent_flag=true alone emits a single 'urgent' badge", () => {
			const c = getListingCardContent(listing({ urgent_flag: true }), t);
			expect(c.badges).toEqual([{ type: "urgent", label: "Срочно" }]);
		});

		it("both flags → both badges, urgent first (priority order)", () => {
			const c = getListingCardContent(
				listing({ urgent_flag: true, is_verified: true }),
				t,
			);
			expect(c.badges.map((b) => b.type)).toEqual(["urgent", "verified"]);
		});

		it("no flags → empty badges array", () => {
			const c = getListingCardContent(listing({}), t);
			expect(c.badges).toEqual([]);
		});

		it("urgent_flag=null is treated as off (DB allows null)", () => {
			const c = getListingCardContent(listing({ urgent_flag: null }), t);
			expect(c.badges).toEqual([]);
		});

		it("urgent_flag=false is treated as off", () => {
			const c = getListingCardContent(
				listing({ urgent_flag: false, is_verified: false }),
				t,
			);
			expect(c.badges).toEqual([]);
		});

		it("is_verified=null is treated as off", () => {
			const c = getListingCardContent(listing({ is_verified: null }), t);
			expect(c.badges).toEqual([]);
		});

		it("badges are independent of property_type / deal_type matrix", () => {
			// Status badges are not matrix-gated — they apply to any listing
			// that carries the flag. (Sale-finance flags are gated separately
			// via financeBadges.)
			for (const pt of ["apartment", "house", "commercial", "land"] as const) {
				for (const dt of ["sell", "rent"] as const) {
					const c = getListingCardContent(
						listing({
							property_type: pt,
							type: dt,
							is_verified: true,
						}),
						t,
					);
					expect(c.badges.some((b) => b.type === "verified")).toBe(true);
				}
			}
		});

		it("badges array does NOT include sale-finance badges (those live in financeBadges)", () => {
			const c = getListingCardContent(
				listing({
					type: "sell",
					mortgage_ok: true,
					halol_ok: true,
					is_verified: true,
				}),
				t,
			);
			expect(c.badges.map((b) => b.type)).toEqual(["verified"]);
			expect(c.financeBadges.map((b) => b.key)).toEqual([
				"mortgage_ok",
				"halol_ok",
			]);
		});
	});
});
