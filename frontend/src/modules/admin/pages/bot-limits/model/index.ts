/**
 * Block D (FU3) — admin bot rate-limit settings state.
 */

import { createEffect, restore } from "effector";

import { apiClient } from "@shared/api/client";

export interface BotRateLimitSettings {
	search_enabled: boolean;
	search_limit: number;
	search_window_sec: number;
	inline_enabled: boolean;
	inline_limit: number;
	inline_window_sec: number;
	limit_message_ru: string;
	limit_message_uz: string;
	limit_message_uz_cyrl: string;
	updated_at?: string | null;
}

export type BotRateLimitUpdate = Omit<BotRateLimitSettings, "updated_at">;

export const fetchBotLimitsFx = createEffect(async () => {
	const response = await apiClient.get<BotRateLimitSettings>(
		"/admin/bot-rate-limits",
	);
	return response.data;
});

export const saveBotLimitsFx = createEffect(
	async (payload: BotRateLimitUpdate) => {
		const response = await apiClient.put<BotRateLimitSettings>(
			"/admin/bot-rate-limits",
			payload,
		);
		return response.data;
	},
);

export const $botLimits = restore<BotRateLimitSettings | null>(
	fetchBotLimitsFx.doneData,
	null,
);

// Keep the store fresh after a successful save (PUT returns the saved row).
$botLimits.on(saveBotLimitsFx.doneData, (_, next) => next);
