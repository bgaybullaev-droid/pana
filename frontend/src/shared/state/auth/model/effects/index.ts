import { createEffect } from "effector";
import { apiClient, stopTokenRefreshTimer } from "@shared/api/client";
import type { AuthResponse, UserMeResponse } from "@shared/api/types";
import { clearStoredTokens } from "@shared/lib/auth-tokens";

export const authenticateWithTelegramFx = createEffect(
	async (initData: string) => {
		const response = await apiClient.post<AuthResponse>("/auth/telegram", {
			init_data: initData,
		});
		return response.data;
	},
);

// Silent session restore on app open inside Telegram. Hits the same
// /auth/telegram endpoint, but is wired to populate $user WITHOUT touching
// $authError — so a previously linked user (telegram_id already on file) is
// re-authenticated with no contact prompt, while a genuinely new user fails
// here quietly and falls through to the PhoneGate (no red error flashes).
export const restoreTelegramSessionFx = createEffect(
	async (initData: string) => {
		const response = await apiClient.post<AuthResponse>("/auth/telegram", {
			init_data: initData,
		});
		return response.data;
	},
);

export const checkSessionFx = createEffect(async () => {
	const response = await apiClient.get<UserMeResponse>("/auth/me");
	return response.data;
});

export const logoutFx = createEffect(async () => {
	stopTokenRefreshTimer();
	clearStoredTokens();
	// Clear any user-specific data from localStorage
	localStorage.removeItem("uchar_preferences");
	// Logout is authoritative locally — swallow backend errors (network down,
	// 401 because the session was already invalid, Telegram WebApp cookie
	// quirks) so the effect's .done event still fires and downstream stores
	// reset. Without this, a failed POST leaves $user populated and the UI
	// thinks the user is still signed in.
	try {
		await apiClient.post("/auth/logout");
	} catch {
		// intentional
	}
});

export const loginWithOLXPhoneFx = createEffect(async (phone: string) => {
	const response = await apiClient.post<AuthResponse>("/auth/olx-phone", {
		phone,
	});
	return response.data;
});

export const loginWithTelegramChannelFx = createEffect(
	async (channelName: string) => {
		const response = await apiClient.post<AuthResponse>(
			"/auth/telegram-channel",
			{
				channel_name: channelName,
			},
		);
		return response.data;
	},
);

export const loginWithBuyerPhoneFx = createEffect(
	async (params: { phone: string; first_name: string; last_name?: string }) => {
		const response = await apiClient.post<AuthResponse>(
			"/auth/buyer-phone",
			params,
		);
		return response.data;
	},
);

export const loginAsAdminFx = createEffect(
	async (params: { username: string; password: string }) => {
		const response = await apiClient.post<AuthResponse>(
			"/auth/admin-login",
			params,
		);
		return response.data;
	},
);

export const requestSellerOTPFx = createEffect(async (phone: string) => {
	// Include Telegram initData if available, so backend can auto-link telegram_id
	const initData = window.Telegram?.WebApp?.initData || undefined;
	const response = await apiClient.post<{
		message: string;
		expires_in: number;
		_dev_otp?: string;
	}>("/auth/seller-otp", { phone, init_data: initData });
	return response.data;
});

export const verifySellerOTPFx = createEffect(
	async (params: { phone: string; otp_code: string }) => {
		const response = await apiClient.post<AuthResponse>(
			"/auth/seller-otp/verify",
			params,
		);
		return response.data;
	},
);

export const devLoginFx = createEffect(async () => {
	const response = await apiClient.post<AuthResponse>("/auth/dev-login");
	return response.data;
});

export const updateProfileFx = createEffect(
	async (data: {
		first_name?: string;
		last_name?: string;
		seller_type?: string;
		seller_telegram?: string;
	}) => {
		const response = await apiClient.patch<UserMeResponse>("/auth/me", data);
		return response.data;
	},
);

// Block D D1 — dedicated language-update effect. Kept separate from
// updateProfileFx so the i18n side-effect wiring (in connections) only
// fires on actual language changes, not every profile edit.
export const updateLanguageFx = createEffect(
	async (language: "ru" | "uz" | "uz_cyrl") => {
		const response = await apiClient.patch<UserMeResponse>("/auth/me", {
			language,
		});
		return response.data;
	},
);
