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
} from "@shared/state/auth/model";
import { PhoneGate } from "@shared/ui/PhoneGate";
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
	const { isReady, isTelegramWebApp } = useTelegram();
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
	}, [isReady, isTelegramWebApp]);

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

	// Phone gate: inside Telegram, block ALL routes until the user has an
	// authenticated session. After checkSessionFx fails, isLoading=false and
	// isAuthenticated=false → PhoneGate drives requestContact() → /auth/telegram.
	const shouldGate =
		isReady && isTelegramWebApp && !isLoading && !isAuthenticated;

	return (
		<AuthContext.Provider value={value}>
			{shouldGate ? <PhoneGate /> : children}
		</AuthContext.Provider>
	);
}
