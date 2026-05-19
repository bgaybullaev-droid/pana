import { createStore } from "effector";
import {
	fetchAutopostStatusFx,
	fetchAutopostPostsFx,
	connectChannelFx,
	disconnectChannelFx,
	type AutopostStatus,
	type AutopostPosts,
} from "../effects";

export const $autopostStatus = createStore<AutopostStatus | null>(null)
	.on(fetchAutopostStatusFx.doneData, (_, data) => data)
	.on(connectChannelFx.doneData, (prev, data) => {
		if (data.status !== "verified") return prev;
		return {
			...(prev ?? {
				connected: true,
				enabled: true,
				channel_username: data.channel_username ?? null,
				channel_id: data.channel_id ?? null,
				verified_at: data.verified_at ?? null,
				stale_count: 0,
			}),
			connected: true,
			enabled: true,
			channel_username: data.channel_username ?? null,
			channel_id: data.channel_id ?? null,
			verified_at: data.verified_at ?? null,
		};
	})
	.on(disconnectChannelFx.done, (prev) => {
		if (!prev) return prev;
		return {
			...prev,
			connected: false,
			enabled: false,
			channel_username: null,
			channel_id: null,
			verified_at: null,
		};
	});

export const $autopostPosts = createStore<AutopostPosts | null>(null).on(
	fetchAutopostPostsFx.doneData,
	(_, data) => data,
);

export const $isLoadingAutopost = createStore<boolean>(false)
	.on(fetchAutopostStatusFx, () => true)
	.on(fetchAutopostStatusFx.finally, () => false);

export const $isConnecting = createStore<boolean>(false)
	.on(connectChannelFx, () => true)
	.on(connectChannelFx.finally, () => false);

export const $connectError = createStore<string | null>(null)
	.on(connectChannelFx, () => null)
	.on(connectChannelFx.doneData, (_, data) =>
		data.status !== "verified" ? data.error ?? "verify_failed" : null,
	)
	.on(connectChannelFx.failData, (_, err) => err.message ?? "error");
