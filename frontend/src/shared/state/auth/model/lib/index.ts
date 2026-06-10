import type { AuthResponse, UserMeResponse } from "@shared/api/types";
import { saveTokens } from "@shared/lib/auth-tokens";
import { startTokenRefreshTimer } from "@shared/api/client";
import type { AuthUser } from "../types";

export const authResponseToUser = (
	data: AuthResponse,
	scope?: string,
): AuthUser => {
	// Save tokens to localStorage
	if (data.access_token) {
		saveTokens(data.access_token, data.refresh_token, scope);
		startTokenRefreshTimer?.();
	}

	return {
		id: data.user_id,
		telegram_id: data.telegram_id,
		first_name: data.first_name,
		last_name: data.last_name,
		username: data.username,
		avatar_url: data.avatar_url,
		role: data.role,
		is_seller: data.is_seller,
		onboarding_completed: data.onboarding_completed,
		approval_status: data.approval_status,
		auth_source: data.auth_source,
		phone: data.phone,
		language: data.language ?? "ru",
		seller_type: data.seller_type ?? null,
		seller_telegram: data.seller_telegram ?? null,
	};
};

export const userMeResponseToUser = (data: UserMeResponse): AuthUser => ({
	id: data.user_id,
	telegram_id: data.telegram_id,
	first_name: data.first_name,
	last_name: data.last_name,
	username: data.username,
	avatar_url: data.avatar_url,
	role: data.role,
	is_seller: data.is_seller,
	onboarding_completed: data.onboarding_completed,
	approval_status: data.approval_status,
	auth_source: data.auth_source,
	phone: data.phone,
	language: data.language ?? "ru",
	seller_type: data.seller_type ?? null,
	seller_telegram: data.seller_telegram ?? null,
});
