import { apiClient } from "./client";
import type { SavedSearch, SavedSearchCreateRequest } from "./types";

const LOCAL_KEY = "uchar_saved_searches_local";

function getLocalSearches(): SavedSearch[] {
	try {
		const raw = localStorage.getItem(LOCAL_KEY);
		let parsed: SavedSearch[] = raw ? JSON.parse(raw) : [];

		// Inject mock search for demonstration if it doesn't exist
		if (!parsed.some(s => s.id === "__mock_demonstration")) {
			const mockSearch: SavedSearch = {
				id: "__mock_demonstration",
				user_id: "local",
				name: "",
				query: "Квартиры с ремонтом",
				filters: {
					deal_type: "sell",
					property_type: "apartment",
					rooms: [2, 3],
					price_max: 65000,
					district: "mirobod"
				},
				sort: "relevance",
				created_at: new Date().toISOString(),
				last_seen_at: new Date().toISOString(),
				new_count: 5, // <--- New listings!
				notifications_enabled: true
			};
			parsed = [mockSearch, ...parsed];
			saveLocalSearches(parsed);
		}

		return parsed;
	} catch {
		return [];
	}
}

function saveLocalSearches(searches: SavedSearch[]) {
	localStorage.setItem(LOCAL_KEY, JSON.stringify(searches));
}

export const savedSearchesApi = {
	/** GET /api/v1/saved-searches — list all with new_count */
	getAll: async (): Promise<SavedSearch[]> => {
		try {
			const { data } = await apiClient.get<SavedSearch[]>("/saved-searches");
			return data;
		} catch {
			// Backend not available — return local fallback
			return getLocalSearches();
		}
	},

	/** POST /api/v1/saved-searches — create a new saved search */
	create: async (payload: SavedSearchCreateRequest): Promise<SavedSearch> => {
		try {
			const { data } = await apiClient.post<SavedSearch>("/saved-searches", payload);
			// Sync to local as backup
			const locals = getLocalSearches().filter(l => !l.id.startsWith("__local_"));
			saveLocalSearches([data, ...locals]);
			return data;
		} catch {
			// Backend not available — save locally
			const localSearch: SavedSearch = {
				id: `__local_${Date.now()}`,
				user_id: "local",
				name: "",
				query: payload.query ?? null,
				filters: payload.filters,
				sort: payload.sort ?? "relevance",
				created_at: new Date().toISOString(),
				last_seen_at: new Date().toISOString(),
				new_count: 0,
			};
			const locals = getLocalSearches();
			saveLocalSearches([localSearch, ...locals]);
			return localSearch;
		}
	},

	/** DELETE /api/v1/saved-searches/{id} */
	delete: async (id: string): Promise<void> => {
		try {
			if (!id.startsWith("__local_")) {
				await apiClient.delete(`/saved-searches/${id}`);
			}
		} catch {
			// Ignore API errors — local removal already happened in store
		}
		// Always remove from local
		saveLocalSearches(getLocalSearches().filter(s => s.id !== id));
	},

	/** PATCH /api/v1/saved-searches/{id}/seen — reset new_count (last_seen_at = now) */
	markSeen: async (id: string): Promise<void> => {
		try {
			if (!id.startsWith("__local_")) {
				await apiClient.patch(`/saved-searches/${id}/seen`);
			}
		} catch {
			// Ignore
		}
	},

	/** PATCH /api/v1/saved-searches/{id}/notifications — toggle notifications */
	toggleNotifications: async (id: string, enabled: boolean): Promise<boolean> => {
		try {
			if (!id.startsWith("__local_")) {
				await apiClient.patch(`/saved-searches/${id}/notifications`, { enabled });
			}
			return enabled;
		} catch {
			// In a real app we might revert state, but here we optimistically return the new state
			return enabled;
		}
	},
};

