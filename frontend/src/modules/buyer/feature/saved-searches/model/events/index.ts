import { createEvent } from "effector";
import type { SavedSearchFilters } from "@shared/api/types";

/** Triggered when user taps the heart icon on search results */
export const toggleSavedSearch = createEvent<{
	query?: string | null;
	filters: SavedSearchFilters;
	sort?: string;
	/** If provided, this search exists and should be deleted instead */
	existingId?: string;
}>();

/** Triggered when user opens the Searches tab (resets new_count) */
export const savedSearchesTabOpened = createEvent();

/** Triggered when user toggles notifications for a saved search */
export const toggleSavedSearchNotifications = createEvent<{ id: string; enabled: boolean }>();
