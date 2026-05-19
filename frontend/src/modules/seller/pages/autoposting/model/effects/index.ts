import { createEffect } from "effector";
import { apiClient } from "@shared/api/client";

export type AutopostStatus = {
	connected: boolean;
	enabled: boolean;
	channel_username: string | null;
	channel_id: number | null;
	verified_at: string | null;
	stale_count: number;
};

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

export type UpdatePostResponse = {
	result: "queued" | "media_too_old" | string;
	post_age_hours?: number;
};

export const fetchAutopostStatusFx = createEffect<void, AutopostStatus>(
	async () => {
		const res = await apiClient.get<AutopostStatus>("/seller/autopost/status");
		return res.data;
	},
);

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

export const updateChannelPostFx = createEffect<
	{ postId: string; forceTextOnly: boolean },
	UpdatePostResponse
>(async ({ postId, forceTextOnly }) => {
	const res = await apiClient.post<UpdatePostResponse>(
		`/seller/autopost/posts/${postId}/update`,
		{ force_text_only: forceTextOnly },
	);
	return res.data;
});

export const recreateChannelPostFx = createEffect<string, { result: string }>(
	async (postId) => {
		const res = await apiClient.post<{ result: string }>(
			`/seller/autopost/posts/${postId}/recreate`,
		);
		return res.data;
	},
);
