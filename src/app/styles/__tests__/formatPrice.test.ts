import { describe, it, expect, beforeEach } from "vitest";
import { formatPrice } from "../theme";

describe("formatPrice — T-020 period extension", () => {
	beforeEach(() => {
		// Default to Russian locale for deterministic suffixes.
		if (typeof localStorage !== "undefined") {
			localStorage.setItem("i18nextLng", "ru");
		}
	});

	describe("backward compatibility — 2-arg calls unchanged", () => {
		it("USD without period renders as $X", () => {
			expect(formatPrice(120000, "USD")).toBe("$120 000");
		});

		it("UZS without period renders as X sum", () => {
			expect(formatPrice(1500000, "UZS")).toBe("1 500 000 sum");
		});

		it("no currency renders bare number", () => {
			expect(formatPrice(42000)).toBe("42 000");
		});

		it("{period: 'total'} is equivalent to no options", () => {
			expect(formatPrice(120000, "USD", { period: "total" })).toBe(
				formatPrice(120000, "USD"),
			);
		});
	});

	describe("rent period suffixes (RU locale)", () => {
		it("month → '/ мес'", () => {
			expect(formatPrice(1500, "USD", { period: "month" })).toBe(
				"$1 500 / мес",
			);
		});

		it("day → '/ сутки'", () => {
			expect(formatPrice(80, "USD", { period: "day" })).toBe("$80 / сутки");
		});

		it("UZS + month", () => {
			expect(formatPrice(5000000, "UZS", { period: "month" })).toBe(
				"5 000 000 sum / мес",
			);
		});
	});

	describe("UZ locale suffixes", () => {
		beforeEach(() => {
			localStorage.setItem("i18nextLng", "uz");
		});

		it("month → '/ oyiga' in uz", () => {
			expect(formatPrice(1500, "USD", { period: "month" })).toBe(
				"$1 500 / oyiga",
			);
		});

		it("day → '/ kuniga' in uz", () => {
			expect(formatPrice(80, "USD", { period: "day" })).toBe("$80 / kuniga");
		});
	});
});

