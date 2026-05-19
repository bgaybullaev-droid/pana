import { createEffect } from "effector";
import { apiClient } from "@shared/api/client";

// Backend response shapes — mirror of `app/api/v1/referrals.py`.

export type ReferralEvent = {
	referred_user_id: string;
	event_type: string;
	created_at: string;
};

export type ReferralStats = {
	invited_count: number;
	qualified_count: number;
	total_rewards_micros: number;
};

export type ReferralOverview = {
	referral_code: string;
	share_url: string;
	stats: ReferralStats;
	recent_events: ReferralEvent[];
};

export type RegenerateResponse = {
	referral_code: string;
	share_url: string;
};

export const fetchReferralOverviewFx = createEffect<void, ReferralOverview>(
	async () => {
		const res = await apiClient.get<ReferralOverview>("/seller/referrals");
		return res.data;
	},
);

export const regenerateReferralCodeFx = createEffect<void, RegenerateResponse>(
	async () => {
		const res = await apiClient.post<RegenerateResponse>(
			"/seller/referrals/regenerate",
		);
		return res.data;
	},
);
