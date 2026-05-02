import { sample } from "effector";
import { toggleSavedSearch, toggleSavedSearchNotifications } from "../events";
import { createSavedSearchFx, deleteSavedSearchFx, toggleSavedSearchNotificationsFx } from "../effects";

// When toggleSavedSearch fires with an existing ID → delete
sample({
	clock: toggleSavedSearch,
	filter: (payload) => !!payload.existingId,
	fn: (payload) => payload.existingId!,
	target: deleteSavedSearchFx,
});

// When toggleSavedSearch fires without an existing ID → create
sample({
	clock: toggleSavedSearch,
	filter: (payload) => !payload.existingId,
	fn: (payload) => ({
		query: payload.query ?? null,
		filters: payload.filters,
		sort: payload.sort ?? "relevance",
	}),
	target: createSavedSearchFx,
});

// Wire toggle notifications event to effect
sample({
	clock: toggleSavedSearchNotifications,
	target: toggleSavedSearchNotificationsFx,
});
