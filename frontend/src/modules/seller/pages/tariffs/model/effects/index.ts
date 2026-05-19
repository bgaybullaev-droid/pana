import { createEffect } from "effector";
import { apiClient } from "@shared/api/client";

export type TariffsStatus = {
	test_period_active: boolean;
	test_period_started_at: string | null;
	current_listings_total: number;
	trigger_listings: number;
	trigger_days: number;
	days_elapsed: number;
	extra_listing_price_uzs: number;
	cabinet_subscription_price_uzs: number;
	free_listings_per_seller: number;
};

export const fetchTariffsStatusFx = createEffect<void, TariffsStatus>(
	async () => {
		const res = await apiClient.get<TariffsStatus>("/tariffs/status");
		return res.data;
	},
);
