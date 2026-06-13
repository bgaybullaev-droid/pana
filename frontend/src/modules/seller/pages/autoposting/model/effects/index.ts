import { createEffect } from "effector";
import { apiClient } from "@shared/api/client";

// Block D D4 — the autopost effects used across seller surfaces (status,
// post update / recreate) now live in the seller shared-state module, so the
// listing form and "My listings" can reach them without a page→page import.
// Re-exported here so this page's existing imports keep working unchanged.
export {
	fetchAutopostStatusFx,
	updateChannelPostFx,
	recreateChannelPostFx,
} from "@modules/seller/shared/state";
export type {
	AutopostStatus,
	UpdatePostResponse,
} from "@modules/seller/shared/state";

// Page-only state below — the channel history list and the connect /
// disconnect flow are used by this page alone, so they stay local.
export type AutopostPost = {
	id: string;
	listing_id: string;
	listing_title: string | null;
	posted_at: string;
	last_edited_at: string | null;
	is_stale: boolean;
	status: "live" | "sold_marker" | "deleted" | string;
};

export type AutopostPosts = {
	items: AutopostPost[];
	page: number;
	page_size: number;
	total: number;
};

export type ConnectResponse = {
	status: "verified" | "error" | string;
	channel_id?: number | null;
	channel_username?: string | null;
	verified_at?: string | null;
	error?: string | null;
};

export const fetchAutopostPostsFx = createEffect<
	{ page?: number; pageSize?: number },
	AutopostPosts
>(async ({ page = 1, pageSize = 20 } = {}) => {
	const res = await apiClient.get<AutopostPosts>("/seller/autopost/posts", {
		params: { page, page_size: pageSize },
	});
	return res.data;
});

export const connectChannelFx = createEffect<string, ConnectResponse>(
	async (channel) => {
		const res = await apiClient.post<ConnectResponse>(
			"/seller/autopost/connect",
			{ channel },
		);
		return res.data;
	},
);

export const disconnectChannelFx = createEffect<void, { status: string }>(
	async () => {
		const res = await apiClient.post<{ status: string }>(
			"/seller/autopost/disconnect",
		);
		return res.data;
	},
);
