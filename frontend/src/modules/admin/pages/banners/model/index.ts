/**
 * Block phase-2 — admin banners console state.
 *
 * CRUD effects for the /admin/banners endpoints. Image URL is a plain
 * string for v1 (admin pastes a CDN URL).
 */

import { createEffect, createEvent, createStore, sample } from "effector";
import { apiClient } from "@shared/api/client";

export type BannerPlacement =
	| "home_top"
	| "home_inline"
	| "listing_inline";

export type BannerLanguage = "ru" | "uz" | "uz_cyrl" | "*";

export interface Banner {
	id: string;
	title: string;
	image_url: string;
	target_url: string;
	placement: BannerPlacement;
	language: BannerLanguage;
	is_active: boolean;
	starts_at: string;
	ends_at: string | null;
	impressions: number;
	clicks: number;
	created_at: string;
}

export interface BannerCreate {
	title: string;
	image_url: string;
	target_url: string;
	placement: BannerPlacement;
	language: BannerLanguage;
	is_active?: boolean;
	starts_at?: string | null;
	ends_at?: string | null;
}

export interface BannerUpdate extends Partial<BannerCreate> {}

export const fetchBannersFx = createEffect(async () => {
	const response = await apiClient.get<Banner[]>("/admin/banners", {
		params: { limit: 200 },
	});
	return response.data;
});

export const createBannerFx = createEffect(async (body: BannerCreate) => {
	const response = await apiClient.post<Banner>("/admin/banners", body);
	return response.data;
});

export const updateBannerFx = createEffect(
	async ({ id, body }: { id: string; body: BannerUpdate }) => {
		const response = await apiClient.patch<Banner>(
			`/admin/banners/${id}`,
			body,
		);
		return response.data;
	},
);

export const deleteBannerFx = createEffect(async (id: string) => {
	await apiClient.delete(`/admin/banners/${id}`);
	return id;
});

export const bannersReset = createEvent();

export const $banners = createStore<Banner[]>([])
	.on(fetchBannersFx.doneData, (_, list) => list)
	.on(createBannerFx.doneData, (state, banner) => [banner, ...state])
	.on(updateBannerFx.doneData, (state, banner) =>
		state.map((b) => (b.id === banner.id ? banner : b)),
	)
	.on(deleteBannerFx.doneData, (state, id) =>
		state.map((b) => (b.id === id ? { ...b, is_active: false } : b)),
	)
	.reset(bannersReset);

// Auto-refresh after mutations.
sample({ clock: createBannerFx.doneData, target: fetchBannersFx });
sample({ clock: updateBannerFx.doneData, target: fetchBannersFx });
sample({ clock: deleteBannerFx.doneData, target: fetchBannersFx });
