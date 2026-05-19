/**
 * Block D V2.0 (D3) — Telegram Mini App deep-link consumption helpers.
 *
 * Owned by the frontend `StartParamHandler`. Pure data plumbing — no
 * UI concerns leak in here. Anything that resolves a `filter_<id>`
 * share link or normalises a `listing_`/`obj_` prefix routes through
 * this module so emitter and consumer formats stay in lock-step with
 * `backend/app/services/deeplink.py`.
 */

import { apiClient } from "@shared/api/client";

export interface DeepLinkPayload {
	id: string;
	kind: string;
	payload: Record<string, unknown>;
}

/**
 * Parse a Telegram `start_param` value into its prefix + body parts.
 *
 * Returns `null` if the param is empty or has no underscore separator
 * — callers should treat that as "no deep link, fall through to the
 * default landing page".
 */
export function parseStartParam(
	startParam: string | null | undefined,
): { prefix: string; body: string } | null {
	if (!startParam) return null;
	const underscore = startParam.indexOf("_");
	if (underscore <= 0 || underscore === startParam.length - 1) return null;
	return {
		prefix: startParam.slice(0, underscore),
		body: startParam.slice(underscore + 1),
	};
}

/**
 * Resolve a `filter_<short_id>` payload by calling the backend.
 *
 * Returns `null` on 404 / network error — the caller should treat the
 * deep link as inert and land the user on the default home view.
 */
export async function fetchDeepLinkPayload(
	shortId: string,
): Promise<DeepLinkPayload | null> {
	try {
		const res = await apiClient.get<DeepLinkPayload>(
			`/deep-links/${encodeURIComponent(shortId)}`,
		);
		return res.data;
	} catch {
		return null;
	}
}
