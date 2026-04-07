import { createEffect } from "effector";
import { apiClient } from "@shared/api/client";
import type { UserPreferences } from "@shared/api/types";
import { $isAuthenticated } from "@shared/state/auth/model";

export const fetchPreferencesFx = createEffect(
	async (): Promise<UserPreferences | null> => {
		const isAuth = $isAuthenticated.getState();
		if (!isAuth) return null;
		const { data } = await apiClient.get<UserPreferences>("/me/preferences");
		return data;
	},
);

// Note: savePreferencesFx references $preferences which creates a circular dependency
// We handle this by using getState() in the effect
export const savePreferencesFx = createEffect(
	async (prefs: Partial<UserPreferences>) => {
		const isAuth = $isAuthenticated.getState();
		if (isAuth) {
			const { data } = await apiClient.put<UserPreferences>(
				"/me/preferences",
				prefs,
			);
			return data;
		}
		return prefs as UserPreferences;
	},
);
