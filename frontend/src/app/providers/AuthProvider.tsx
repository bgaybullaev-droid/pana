import { createContext, useEffect, useMemo, ReactNode } from "react";
import { useUnit } from "effector-react";
import { useTelegram } from "./useTelegram";
import {
	$user,
	$isAuthenticated,
	$isLoading,
	logout as logoutEvent,
	authCheckComplete,
	devLogin,
	checkSession,
	checkSessionFx,
	restoreTelegramSessionFx,
} from "@shared/state/auth/model";
import { PhoneGate } from "@shared/ui/PhoneGate";
import i18n, { backendToFrontendLocale } from "@shared/i18n";
// Eagerly import user-state connections so the sample() that wires
// checkSessionFx.done → fetchUserStatsFx exists BEFORE checkSessionFx
// fires during page-reload session restore. Without this, the
// connection module only loads when BottomNavigation or HomePage mount
// (which happens AFTER checkSessionFx.done has already fired and been
// missed).
import "@shared/state/user/model";

const DEV_LOGOUT_KEY = "dev_logged_out";
const isDev = import.meta.env.DEV || import.meta.env.VITE_ENV === "development";

interface AuthContextValue {
	user: ReturnType<typeof $user.getState>;
	isAuthenticated: boolean;
	isLoading: boolean;
	isPendingApproval: boolean;
	isRejected: boolean;
	isApproved: boolean;
	logout: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
	user: null,
	isAuthenticated: false,
	isLoading: true,
	isPendingApproval: false,
	isRejected: false,
	isApproved: false,
	logout: () => {},
});

interface AuthProviderProps {
	children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
	const { isReady, isTelegramWebApp, initData, user: tgUser } = useTelegram();
	const [user, isAuthenticated, isLoading] = useUnit([
		$user,
		$isAuthenticated,
		$isLoading,
	]);

	useEffect(() => {
		if (!isReady) return;

		const init = async () => {
			// Phone-gated flow: initData alone is NEVER sufficient to auth.
			// Always try cookie-based session restore first. If that fails,
			// - Inside Telegram: PhoneGate handles requestContact() → re-auth.
			// - Outside Telegram (dev-web): fall back to devLogin / phone OTP.
			try {
				await checkSessionFx();
				return;
			} catch {
				// No valid session — fall through
			}

			if (isTelegramWebApp) {
				// Before gating, try a SILENT re-auth with initData. A user who
				// is already linked (telegram_id on file) is authenticated by
				// the backend with no contact prompt — this is what lets a
				// registered user open a channel deep-link without being asked
				// to share their phone every time. Only a genuinely new/unlinked
				// user fails here (PHONE_REQUIRED) and falls through to the gate.
				if (initData) {
					try {
						await restoreTelegramSessionFx(initData);
						return;
					} catch {
						// Not linked yet — fall through to PhoneGate.
					}
				}
				// Stop the loading spinner so PhoneGate renders.
				authCheckComplete();
				return;
			}

			const hasDevLoggedOut = localStorage.getItem(DEV_LOGOUT_KEY) === "true";
			if (isDev && !hasDevLoggedOut) {
				devLogin();
			} else {
				authCheckComplete();
			}
		};

		init();
	}, [isReady, isTelegramWebApp, initData]);

	// Telegram account-switch defense. The Mini App runs in a single WebView
	// per Telegram client — cookies and localStorage persist across account
	// switches. If the user hops from account A to account B inside Telegram
	// and reopens the app, our stale cookie would keep them "logged in" as A
	// (because /auth/me validates the JWT, not the active Telegram identity).
	//
	// This effect fires whenever $user or the active Telegram user changes
	// and forces a logout when the two disagree. The next render hits
	// shouldGate=true and PhoneGate drives a fresh /auth/telegram under the
	// correct identity.
	useEffect(() => {
		if (!isTelegramWebApp) return;
		if (!user || tgUser?.id == null) return;
		if (user.telegram_id != null && user.telegram_id !== tgUser.id) {
			logoutEvent();
		}
	}, [isTelegramWebApp, user, tgUser?.id]);

	// Re-fetch session when user switches back to the app (e.g. after bot registration)
	useEffect(() => {
		const handleVisibilityChange = () => {
			if (document.visibilityState === "visible" && user) {
				checkSession();
			}
		};
		document.addEventListener("visibilitychange", handleVisibilityChange);
		return () =>
			document.removeEventListener("visibilitychange", handleVisibilityChange);
	}, [user]);

	// Block D D1 — sync i18n locale from backend on every $user change.
	// Backend value ("ru" | "uz" | "uz_cyrl") is the single source of
	// truth; the local i18n locale follows. Avoid a redundant
	// changeLanguage() if it already matches (prevents the listing-content
	// callbacks in i18n/index.ts from firing on every render).
	useEffect(() => {
		if (!user?.language) return;
		const desired = backendToFrontendLocale(user.language);
		if (i18n.language !== desired) {
			i18n.changeLanguage(desired);
		}
	}, [user?.language]);

	// Logout handler that persists logout state in dev mode
	const handleLogout = () => {
		if (isDev) {
			localStorage.setItem(DEV_LOGOUT_KEY, "true");
		}
		logoutEvent();
	};

	// Compute approval status flags
	const approvalStatus = useMemo(() => {
		if (!user) {
			return { isPendingApproval: false, isRejected: false, isApproved: false };
		}
		return {
			isPendingApproval: user.approval_status === "pending",
			isRejected: user.approval_status === "rejected",
			isApproved: user.approval_status === "approved",
		};
	}, [user]);

	const value: AuthContextValue = {
		user,
		isAuthenticated,
		isLoading,
		isPendingApproval: approvalStatus.isPendingApproval,
		isRejected: approvalStatus.isRejected,
		isApproved: approvalStatus.isApproved,
		logout: handleLogout,
	};

	// Telegram account-switch: true when the restored session's telegram_id
	// doesn't match the currently-active Telegram account. The useEffect
	// above fires logoutEvent to clean up async, but we also need to block
	// rendering synchronously on this render so Account A's UI never flashes.
	const telegramIdMismatch =
		isTelegramWebApp &&
		user != null &&
		tgUser?.id != null &&
		user.telegram_id != null &&
		user.telegram_id !== tgUser.id;

	// Phone gate: inside Telegram, block ALL routes until the user has an
	// authenticated session matching the active Telegram account. After
	// checkSessionFx fails, isLoading=false and isAuthenticated=false →
	// PhoneGate drives requestContact() → /auth/telegram.
	const shouldGate =
		isReady &&
		isTelegramWebApp &&
		!isLoading &&
		(!isAuthenticated || telegramIdMismatch);

	return (
		<AuthContext.Provider value={value}>
			{shouldGate ? <PhoneGate /> : children}
		</AuthContext.Provider>
	);
}
