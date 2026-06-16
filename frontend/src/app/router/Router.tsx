import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { Suspense, lazy, useEffect, useRef } from "react";
import { LoadingOverlay } from "@mantine/core";
import { useUnit } from "effector-react";
import { useTelegram } from "@app/providers/useTelegram";
import { $backHandlers } from "@shared/lib/telegram/backStack";
import { parseStartParam, fetchDeepLinkPayload } from "@shared/lib/deepLinks";

// Auth pages (kept local to shell)
const AuthPage = lazy(() =>
	import("@app/pages/auth").then((m) => ({ default: m.AuthPage })),
);

// Lazy-load module routers
const UserRouter = lazy(() =>
	import("@modules/buyer/app").then((m) => ({ default: m.UserRouter })),
);
const AdminRouter = lazy(() =>
	import("@modules/admin/app").then((m) => ({ default: m.AdminRouter })),
);

// Map a resolved filter payload onto the buyer-feed URL params the home
// page hydrates from on mount (see home/ui/page/Page.tsx "Initialize from
// URL params"). The payload can come from three sources with two key
// vocabularies, all handled here:
//   • bot search / marketing slug — scalar `deal_type`, `rooms_min/max`,
//     scalar `district` (legacy, kept for already-shared links);
//   • the in-app "Share filter" action — the full `HomeFilters` shape
//     (arrays + every advanced filter).
// Unknown/malformed fields are skipped; an empty result lands the user on
// the plain (unfiltered) home rather than crashing.
function buildFilterSearch(raw: Record<string, unknown>): string {
	const params = new URLSearchParams();

	const setStr = (key: string, v: unknown) => {
		if (typeof v === "string" && v) params.set(key, v);
	};
	const setNum = (key: string, v: unknown) => {
		const n = Number(v);
		if (Number.isFinite(n) && n > 0) params.set(key, String(n));
	};
	const setBool = (key: string, v: unknown) => {
		if (v === true || v === "true") params.set(key, "true");
	};
	const setList = (key: string, v: unknown) => {
		if (Array.isArray(v)) {
			const items = v.filter((x) => x != null && x !== "");
			if (items.length) params.set(key, items.join(","));
		} else if (typeof v === "string" && v) {
			params.set(key, v);
		} else if (typeof v === "number" && Number.isFinite(v)) {
			params.set(key, String(v));
		}
	};

	setStr("q", raw.q);

	// Deal type: HomeFilters `type` (array) or the bot/slug `deal_type` (scalar).
	if (raw.type != null) setList("type", raw.type);
	else if (raw.deal_type === "sell" || raw.deal_type === "rent") {
		params.set("type", raw.deal_type);
	}

	setList("property_type", raw.property_type);
	setList("region", raw.region);
	setList("district", raw.district);

	// Rooms: HomeFilters `rooms` array, or the bot's rooms_min..rooms_max
	// range. Capped at 5 (the feed bins "5+" into a single 5 chip).
	const rooms = new Set<number>();
	if (Array.isArray(raw.rooms)) {
		for (const r of raw.rooms) {
			const n = Number(r);
			if (Number.isFinite(n) && n > 0) rooms.add(Math.min(n, 5));
		}
	} else {
		const min = Number(raw.rooms_min);
		const max = Number(raw.rooms_max ?? raw.rooms_min);
		if (Number.isFinite(min) && min > 0) {
			const ceiling = Math.min(Number.isFinite(max) && max >= min ? max : min, 5);
			for (let r = Math.max(1, min); r <= ceiling; r++) rooms.add(r);
		}
	}
	if (rooms.size) {
		params.set("rooms", [...rooms].sort((a, b) => a - b).join(","));
	}

	setNum("price_min", raw.price_min);
	setNum("price_max", raw.price_max);
	setNum("area_min", raw.area_min);
	setNum("area_max", raw.area_max);
	setNum("floor_min", raw.floor_min);
	setNum("floor_max", raw.floor_max);
	setNum("total_floors_min", raw.total_floors_min);
	setNum("total_floors_max", raw.total_floors_max);
	setNum("posted_within", raw.posted_within);

	setBool("not_first_floor", raw.not_first_floor);
	setBool("not_last_floor", raw.not_last_floor);
	setBool("has_photo", raw.has_photo);
	setBool("mortgage_ok", raw.mortgage_ok);
	setBool("installment_ok", raw.installment_ok);
	setBool("halol_ok", raw.halol_ok);
	setBool("furnished", raw.furnished);
	setBool("allowed_pets", raw.allowed_pets);
	setBool("allowed_students", raw.allowed_students);
	setBool("utilities_incl", raw.utilities_incl);

	setStr("building_type", raw.building_type);
	setList("condition", raw.condition);
	setStr("rent_period", raw.rent_period);
	setStr("sort", raw.sort);

	return params.toString();
}

/**
 * Telegram Mini App deep-link consumer (Block D D3).
 *
 * Recognises four inbound payload shapes:
 *   listing_<uuid>   open listing-detail page
 *   obj_<uuid>       alias of listing_ (DECISION_MATRIX D3-Q1)
 *   filter_<id>      fetch payload from /deep-links/{id}, hydrate filter store
 *   <anything else>  ignored — the user lands on the default route
 *
 * Claim/agent/ref/inv/link payloads are bot-side flows; they never
 * arrive here because Telegram routes them to the bot chat, not the
 * Mini App.
 */
function StartParamHandler() {
	const { webApp } = useTelegram();
	const navigate = useNavigate();
	const handledRef = useRef(false);

	useEffect(() => {
		if (handledRef.current) return;
		const startParam = webApp?.initDataUnsafe?.start_param;

		// Bare-token deep links (no "_" body) — parseStartParam returns
		// null for these, so they must be handled before the
		// prefix/body split. "found" is emitted by the grouped
		// crawled-match push (Block A — A4 group-batching).
		if (startParam === "found") {
			handledRef.current = true;
			navigate("/seller/found", { replace: true });
			return;
		}

		const parsed = parseStartParam(startParam);
		if (parsed == null) return;
		handledRef.current = true;

		const { prefix, body } = parsed;

		if (prefix === "listing" || prefix === "obj") {
			navigate(`/listings/${body}`, { replace: true });
			return;
		}

		if (prefix === "filter") {
			// Fire-and-forget: resolve the payload, then land on home with
			// the filter encoded as URL params — the home page hydrates its
			// feed filters from these on mount. Network failure (or an
			// undecodable link) is silent: the user just sees the
			// unfiltered home.
			(async () => {
				const data = await fetchDeepLinkPayload(body);
				const qs =
					data && data.kind === "filter"
						? buildFilterSearch(data.payload)
						: "";
				navigate(qs ? `/?${qs}` : "/", { replace: true });
			})();
			return;
		}

		// Unknown prefix — quiet degradation, the user proceeds on the
		// default route. The bot side has already logged this entry.
	}, [webApp, navigate]);

	return null;
}

// Automatically manages Telegram's native top-bar (Back button) based on routing
function TelegramBackButtonManager() {
	const { webApp } = useTelegram();
	const navigate = useNavigate();
	const location = useLocation();
	// Open overlays (drawers / modals) intercept Back: it closes the
	// topmost one instead of navigating. See useTelegramBackClose.
	const backHandlers = useUnit($backHandlers);
	const hasOverlay = backHandlers.length > 0;

	useEffect(() => {
		// BackButton requires Telegram WebApp 6.1+. Older clients (e.g. 6.0)
		// emit "BackButton is not supported in version X.Y" warnings when
		// .show/.hide/.onClick are called. Fall back silently — users on
		// old clients just won't have an in-app back button.
		if (!webApp?.BackButton || !webApp.isVersionAtLeast?.("6.1")) return;

		// Paths where we only want to display "Close" natively. Top-level
		// tabs (Favorites, Settings) intentionally show Back instead — it
		// returns the user to the section they came from, matching the
		// Android system-back convention (tab → home → exit).
		const rootPaths = ["/", "/search", "/auth"];
		const isRootPath = rootPaths.includes(location.pathname);

		if (hasOverlay || !isRootPath) {
			webApp.BackButton.show();
		} else {
			webApp.BackButton.hide();
		}

		const handleBackClick = () => {
			// Read the stack live — overlays may open/close between the
			// subscription render and the actual click.
			const stack = $backHandlers.getState();
			const topOverlay = stack[stack.length - 1];
			if (topOverlay) {
				topOverlay();
				return;
			}
			// Direct deep-link entries have no in-app history (idx 0) —
			// going back would leave the SPA, so route to home instead.
			if (window.history.state && window.history.state.idx > 0) {
				navigate(-1);
			} else {
				navigate("/", { replace: true });
			}
		};

		webApp.BackButton.onClick(handleBackClick);

		return () => {
			webApp.BackButton.offClick(handleBackClick);
		};
	}, [webApp, location.pathname, navigate, hasOverlay]);

	return null;
}

export function Router() {
	const { isReady } = useTelegram();

	// Show loading while checking Telegram
	if (!isReady) {
		return <LoadingOverlay visible />;
	}

	return (
		<Suspense fallback={<LoadingOverlay visible />}>
			<StartParamHandler />
			<TelegramBackButtonManager />
			<Routes>
				{/* Auth routes (shell-level) */}
				<Route path="/auth" element={<AuthPage />} />

				{/* Admin module */}
				<Route path="/admin/*" element={<AdminRouter />} />

				{/* User module (catch-all — includes buyer + seller pages) */}
				<Route path="/*" element={<UserRouter />} />
			</Routes>
		</Suspense>
	);
}
