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
// URL params"). The payload comes either from a stored short-id row or
// from a synthesised marketing slug (FU6) — both share the bot's key
// shape (district / rooms_min / rooms_max / deal_type / price_*). Unknown
// or malformed fields are skipped; an empty result lands the user on the
// plain (unfiltered) home rather than crashing.
function buildFilterSearch(raw: Record<string, unknown>): string {
	const params = new URLSearchParams();

	if (typeof raw.district === "string" && raw.district) {
		params.set("district", raw.district);
	}
	if (raw.deal_type === "sell" || raw.deal_type === "rent") {
		params.set("type", raw.deal_type);
	}
	if (typeof raw.property_type === "string" && raw.property_type) {
		params.set("property_type", raw.property_type);
	}

	// rooms_min..rooms_max → discrete multiselect chips, capped at 5
	// (the feed bins "5+" into a single 5 chip).
	const min = Number(raw.rooms_min);
	const rawMax = raw.rooms_max ?? raw.rooms_min;
	const max = Number(rawMax);
	if (Number.isFinite(min) && min > 0) {
		const ceiling = Math.min(Number.isFinite(max) && max >= min ? max : min, 5);
		const rooms: number[] = [];
		for (let r = Math.max(1, min); r <= ceiling; r++) rooms.push(r);
		if (rooms.length) params.set("rooms", rooms.join(","));
	}

	const priceMin = Number(raw.price_min);
	if (Number.isFinite(priceMin) && priceMin > 0) {
		params.set("price_min", String(priceMin));
	}
	const priceMax = Number(raw.price_max);
	if (Number.isFinite(priceMax) && priceMax > 0) {
		params.set("price_max", String(priceMax));
	}

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
