import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { Suspense, lazy, useEffect, useRef } from "react";
import { LoadingOverlay } from "@mantine/core";
import { useUnit } from "effector-react";
import { useTelegram } from "@app/providers/useTelegram";
import { $backHandlers } from "@shared/lib/telegram/backStack";
import { parseStartParam, fetchDeepLinkPayload } from "@shared/lib/deepLinks";
import { filtersApplied } from "@modules/buyer/feature/filter/model";
import type { BuyerFilterState } from "@shared/api/types";

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

// Coerce a raw payload dict into BuyerFilterState shape. Unknown / missing
// fields fall back to defaults so a malformed payload row can't crash
// the home page — worst case the user sees an unfiltered list.
function coerceFilterPayload(raw: Record<string, unknown>): BuyerFilterState {
	const sorting =
		typeof raw.sortingSelected === "number" ? raw.sortingSelected : -1;
	const priceRange = Array.isArray(raw.priceRange) && raw.priceRange.length === 2
		? [Number(raw.priceRange[0]) || 0, Number(raw.priceRange[1]) || 2000000]
		: [0, 2000000];
	const regions = Array.isArray(raw.regions)
		? raw.regions.filter((x): x is string => typeof x === "string")
		: [];
	return {
		sortingSelected: sorting,
		priceRange: priceRange as [number, number],
		regions,
	};
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
			// Fire-and-forget: hydrate the filter store, then land on home.
			// Network failure is silent — user just sees the unfiltered home.
			(async () => {
				const data = await fetchDeepLinkPayload(body);
				if (data && data.kind === "filter") {
					filtersApplied(coerceFilterPayload(data.payload));
				}
				navigate("/", { replace: true });
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
