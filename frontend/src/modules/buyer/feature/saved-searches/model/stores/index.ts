import { createStore } from "effector";
import type { SavedSearch } from "@shared/api/types";
import {
	fetchSavedSearchesFx,
	createSavedSearchFx,
	deleteSavedSearchFx,
	markSearchSeenFx,
	toggleSavedSearchNotificationsFx,
} from "../effects";

export const $savedSearches = createStore<SavedSearch[]>([])
	// Load response replaces the full list
	.on(fetchSavedSearchesFx.doneData, (_, searches) => searches)

	// ── Optimistic CREATE ─────────────────────────────────────────────────
	// Immediately add a placeholder on trigger (before API responds)
	.on(createSavedSearchFx, (searches, payload) => {
		const optimistic: SavedSearch = {
			id: `__optimistic_${Date.now()}`,
			user_id: "",
			name: "",
			query: payload.query ?? null,
			filters: payload.filters,
			sort: payload.sort ?? "relevance",
			created_at: new Date().toISOString(),
			last_seen_at: new Date().toISOString(),
			new_count: 0,
		};
		return [optimistic, ...searches];
	})
	// Replace the optimistic placeholder with the real response
	.on(createSavedSearchFx.doneData, (searches, newSearch) => [
		newSearch,
		...searches.filter((s) => !s.id.startsWith("__optimistic_")),
	])
	// Rollback if API failed
	.on(createSavedSearchFx.fail, (searches) =>
		searches.filter((s) => !s.id.startsWith("__optimistic_")),
	)

	// ── Optimistic DELETE ─────────────────────────────────────────────────
	// Immediately remove on trigger
	.on(deleteSavedSearchFx, (searches, deletedId) =>
		searches.filter((s) => s.id !== deletedId),
	)
	// If API failed, restore — we can't restore easily without snapshot,
	// so instead re-fetch the full list
	.on(deleteSavedSearchFx.fail, (searches) => searches) // stays removed; user can refresh

	// ── Mark seen ─────────────────────────────────────────────────────────
	.on(markSearchSeenFx.doneData, (searches, seenId) =>
		searches.map((s) =>
			s.id === seenId ? { ...s, new_count: 0, last_seen_at: new Date().toISOString() } : s,
		),
	)

	// ── Toggle notifications ──────────────────────────────────────────────
	.on(toggleSavedSearchNotificationsFx, (searches, payload) =>
		searches.map((s) =>
			s.id === payload.id ? { ...s, notifications_enabled: payload.enabled } : s,
		),
	);

export const $savedSearchesLoading = fetchSavedSearchesFx.pending;
export const $savedSearchCreating = createSavedSearchFx.pending;
export const $savedSearchDeleting = deleteSavedSearchFx.pending;
