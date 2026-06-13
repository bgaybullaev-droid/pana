import { createStore } from "effector";
import {
	fetchAutopostStatusFx,
	connectChannelFx,
	fetchAutopostPostsFx,
	type AutopostPosts,
} from "../effects";

// Block D D4 — the canonical autopost status store lives in the seller
// shared-state module (the listing form consumes it too). Re-exported here so
// this page keeps importing `$autopostStatus` from its own model. It reacts to
// `fetchAutopostStatusFx` only; this page re-fetches after connect/disconnect.
export { $autopostStatus } from "@modules/seller/shared/state";

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
