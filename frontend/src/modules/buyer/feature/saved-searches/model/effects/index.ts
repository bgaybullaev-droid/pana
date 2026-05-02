import { createEffect } from "effector";
import { savedSearchesApi } from "@shared/api/savedSearches";
import { activityLogApi } from "@shared/api/activityLog";
import { $isAuthenticated } from "@shared/state/auth/model";
import type { SavedSearch, SavedSearchCreateRequest } from "@shared/api/types";

export const fetchSavedSearchesFx = createEffect(
	async (): Promise<SavedSearch[]> => {
		const isAuth = $isAuthenticated.getState();
		if (!isAuth) return [];
		return savedSearchesApi.getAll();
	},
);

export const createSavedSearchFx = createEffect(
	async (payload: SavedSearchCreateRequest): Promise<SavedSearch> => {
		const result = await savedSearchesApi.create(payload);
		// Log activity for backend intelligence (Ф-78)
		activityLogApi.log({
			action: "save_search",
			query: payload.query ?? undefined,
			filters: payload.filters as Record<string, unknown>,
		});
		return result;
	},
);

export const deleteSavedSearchFx = createEffect(
	async (id: string): Promise<string> => {
		await savedSearchesApi.delete(id);
		return id;
	},
);

export const markSearchSeenFx = createEffect(
	async (id: string): Promise<string> => {
		await savedSearchesApi.markSeen(id);
		return id;
	},
);

export const toggleSavedSearchNotificationsFx = createEffect(
	async (payload: { id: string; enabled: boolean }): Promise<{ id: string; enabled: boolean }> => {
		await savedSearchesApi.toggleNotifications(payload.id, payload.enabled);
		return payload;
	}
);
