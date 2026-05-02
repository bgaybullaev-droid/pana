import { createEvent } from "effector";
import {
	toggleFavorite,
	$favoritedIds,
	fetchFavoriteIdsFx,
	searchQueryChanged,
	applyFilters,
	clearFilters,
} from "@modules/buyer/shared/state/model";
import type { HomeFilters } from "../types";

export const pageOpened = createEvent();
export const loadMore = createEvent();
export const resetListings = createEvent();
export { toggleFavorite, $favoritedIds, fetchFavoriteIdsFx };
export { searchQueryChanged, applyFilters, clearFilters };
export const filtersChanged = createEvent<Partial<HomeFilters>>();
