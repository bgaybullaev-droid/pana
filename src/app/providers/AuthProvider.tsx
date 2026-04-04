import { createContext, useEffect, useMemo, ReactNode } from "react";
import { useUnit } from "effector-react";
import { useTelegram } from "./useTelegram";
import {
	$user,
	$isAuthenticated,
	$isLoading,
	authenticateWithTelegram,
	logout as logoutEvent,
	authCheckComplete,
	devLogin,
	checkSession,
	checkSessionFx,
} from "@shared/state/auth/model";

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
	const { initData, isReady, isTelegramWebApp } = useTelegram();
	const [user, isAuthenticated, isLoading] = useUnit([
		$user,
		$isAuthenticated,
		$isLoading,
	]);

	useEffect(() => {
		if (!isReady) return;

		const init = async () => {
			// In Telegram WebApp: authenticate with initData
			// User will only be "authenticated" if they have a phone number
			// (controlled by $isAuthenticated store)
			if (initData && isTelegramWebApp) {
				authenticateWithTelegram(initData);
				return;
			}

			// Non-Telegram: try restoring session from stored token
			try {
				await checkSessionFx();
				return;
			} catch {
				// Session invalid — fall through
			}

			const hasDevLoggedOut = localStorage.getItem(DEV_LOGOUT_KEY) === "true";
			if (isDev && !hasDevLoggedOut) {
				devLogin();
			} else {
				authCheckComplete();
			}
		};

		init();
	}, [isReady, initData, isTelegramWebApp]);

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

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
