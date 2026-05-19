/**
 * Block F V2.0 (F4b) — seller text-export state.
 */

import { createEffect, restore } from "effector";

import { apiClient } from "@shared/api/client";

export type ExportPlatform = "olx" | "telegram_channel" | "instagram" | "pack";

export interface ExportResponse {
	platform: string;
	text: string;
	title: string | null;
	truncated: boolean;
}

export interface ExportPackItem {
	platform: string;
	text: string;
	title: string | null;
	truncated: boolean;
}

export interface ExportPackResponse {
	items: ExportPackItem[];
}

export interface ExportSettings {
	signature: string | null;
	cta: string | null;
	extra_hashtags: string | null;
}

export const fetchExportFx = createEffect(
	async ({
		listingId,
		platform,
		lang = "ru",
	}: {
		listingId: string;
		platform: ExportPlatform;
		lang?: string;
	}) => {
		const response = await apiClient.get<ExportResponse | ExportPackResponse>(
			`/seller/exports/${listingId}/${platform}`,
			{ params: { lang } },
		);
		return response.data;
	},
);

export const fetchExportSettingsFx = createEffect(async () => {
	const response = await apiClient.get<ExportSettings>(
		"/seller/exports/settings",
	);
	return response.data;
});

export const $exportSettings = restore<ExportSettings | null>(
	fetchExportSettingsFx.doneData,
	null,
);

export const updateExportSettingsFx = createEffect(
	async (payload: Partial<ExportSettings>) => {
		const response = await apiClient.patch<ExportSettings>(
			"/seller/exports/settings",
			payload,
		);
		return response.data;
	},
);
