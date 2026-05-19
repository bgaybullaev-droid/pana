import { apiClient } from "@shared/api/client";

const ANON_COOKIE_NAME = "ucm_anon";
const ANON_COOKIE_MAX_AGE_SEC = 60 * 60 * 24; // 24h TTL per A5 V2.0

/** Read or lazily-create the anonymous-viewer id cookie. */
function getOrCreateAnonId(): string | null {
	if (typeof document === "undefined") return null;
	const match = document.cookie
		.split("; ")
		.find((c) => c.startsWith(`${ANON_COOKIE_NAME}=`));
	if (match) {
		const v = match.slice(ANON_COOKIE_NAME.length + 1);
		if (v && v.length >= 8) return v;
	}
	// Generate a URL-safe 22-char id (~128 bits of entropy)
	let id = "";
	if (typeof crypto !== "undefined" && crypto.getRandomValues) {
		const buf = new Uint8Array(16);
		crypto.getRandomValues(buf);
		id = btoa(String.fromCharCode(...buf))
			.replace(/\+/g, "-")
			.replace(/\//g, "_")
			.replace(/=+$/, "");
	} else {
		id =
			Math.random().toString(36).slice(2) +
			Math.random().toString(36).slice(2);
	}
	document.cookie = `${ANON_COOKIE_NAME}=${id}; max-age=${ANON_COOKIE_MAX_AGE_SEC}; path=/; SameSite=Lax`;
	return id;
}

/**
 * Per-user view-tracking dispatcher.
 *
 * Mounts on a listing render: fires an immediate `POST /listings/{id}/view`
 * with no dwell, then schedules a follow-up that includes dwell time on
 * unmount, page-hide, or pagehide.
 *
 * Per A5 V2.0:
 * - Authenticated users send their user_id (server-side via auth dep).
 * - Anonymous users send a stable cookie-backed `anon_id` so per-day
 *   dedup applies to anon traffic too.
 * - Failures are fire-and-forget; telemetry never blocks the UI.
 *
 * Returns a cleanup function. Call it from React `useEffect` cleanup or
 * Swiper `slideChange` to flush the dwell event for the previous slide.
 */
export function trackView(
	listingId: string,
	isAuthenticated: boolean,
): () => void {
	const anonId = isAuthenticated ? null : getOrCreateAnonId();
	const startedAt = performance.now();
	let sent = false;

	apiClient
		.post(`/listings/${listingId}/view`, {
			dwell_ms: null,
			anon_id: anonId,
		})
		.catch(() => {
			/* fire-and-forget */
		});

	const fireDwell = () => {
		if (sent) return;
		sent = true;

		const dwellMs = Math.round(performance.now() - startedAt);
		// pagehide/unload paths require sendBeacon — apiClient (XHR) is
		// killed by the navigation. If beacon is unavailable, drop the
		// dwell event silently; it's fire-and-forget telemetry.
		try {
			const url = `${apiClient.defaults.baseURL}/listings/${listingId}/view`;
			const body = JSON.stringify({ dwell_ms: dwellMs, anon_id: anonId });
			const blob = new Blob([body], { type: "application/json" });
			navigator.sendBeacon?.(url, blob);
		} catch {
			/* fire-and-forget */
		}
	};

	const onVisibility = () => {
		if (document.visibilityState === "hidden") fireDwell();
	};

	document.addEventListener("visibilitychange", onVisibility);
	window.addEventListener("pagehide", fireDwell);

	return () => {
		document.removeEventListener("visibilitychange", onVisibility);
		window.removeEventListener("pagehide", fireDwell);
		fireDwell();
	};
}

/**
 * Record a single contact event. The button's optimistic UI proceeds
 * even on failure — telemetry must never block the seller-contact flow.
 */
export async function trackContact(
	listingId: string,
	isAuthenticated: boolean = false,
): Promise<void> {
	// When `isAuthenticated` is unknown (omitted), the cookie-backed anon_id
	// is sent. The server's auth dep will still pick up the bearer token if
	// present, in which case anon_id is ignored on the auth path.
	const anonId = isAuthenticated ? null : getOrCreateAnonId();
	try {
		await apiClient.post(`/listings/${listingId}/contact`, { anon_id: anonId });
	} catch {
		/* fire-and-forget */
	}
}
