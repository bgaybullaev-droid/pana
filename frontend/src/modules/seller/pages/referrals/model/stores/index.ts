import { createStore } from "effector";
import {
	fetchReferralOverviewFx,
	regenerateReferralCodeFx,
	type ReferralOverview,
} from "../effects";

export const $referralOverview = createStore<ReferralOverview | null>(null)
	.on(fetchReferralOverviewFx.doneData, (_, data) => data)
	.on(regenerateReferralCodeFx.doneData, (prev, data) => {
		if (!prev) return prev;
		return {
			...prev,
			referral_code: data.referral_code,
			share_url: data.share_url,
		};
	});

export const $isLoadingReferrals = createStore<boolean>(false)
	.on(fetchReferralOverviewFx, () => true)
	.on(fetchReferralOverviewFx.finally, () => false);

export const $isRegenerating = createStore<boolean>(false)
	.on(regenerateReferralCodeFx, () => true)
	.on(regenerateReferralCodeFx.finally, () => false);
