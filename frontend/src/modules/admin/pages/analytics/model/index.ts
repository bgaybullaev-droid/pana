/**
 * Block phase-2 — admin analytics (price-index) state.
 *
 * Pure-fetch effect: the page itself owns the filter form state in
 * local component state. We expose a single effect + restored store
 * so the page reuses the standard ``effector-react`` ``useUnit``
 * pattern the other admin pages already follow.
 */

import { createEffect, restore } from "effector";

import { apiClient } from "@shared/api/client";

export interface PriceIndexQuery {
	district?: string;
	property_type?: "apartment" | "house" | "commercial" | "land";
	rooms?: number;
	window_days?: number;
}

export interface PriceIndexResult {
	sample_size: number;
	median: number | null;
	p25: number | null;
	p75: number | null;
	currency: string;
	window_days: number;
}

export const fetchPriceIndexFx = createEffect(
	async (query: PriceIndexQuery): Promise<PriceIndexResult> => {
		const response = await apiClient.get<PriceIndexResult>(
			"/analytics/price-index",
			{ params: query },
		);
		return response.data;
	},
);

export const $priceIndex = restore<PriceIndexResult | null>(
	fetchPriceIndexFx.doneData,
	null,
);
