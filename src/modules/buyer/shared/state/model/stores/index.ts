import { createStore } from "effector";
import { logoutFx } from "@shared/state/auth/model";
import {
	fetchFavoriteIdsFx,
	addFavoriteFx,
	removeFavoriteFx,
} from "../effects";
import {
	searchQueryChanged,
	clearFilters,
	seedListingIds,
	seedListingSource,
} from "../events";

// Seed stores — shared so they're populated BEFORE the lazy detail page loads
export const $sharedSeedIds = createStore<string[]>([]).on(
	seedListingIds,
	(_, ids) => [...new Set(ids)],
);

export const $sharedSeedSource = createStore<"feed" | "finite">("feed").on(
	seedListingSource,
	(_, source) => source,
);

export const $searchQuery = createStore("")
	.on(searchQueryChanged, (_, q) => q)
	.reset(clearFilters);

export const $favoritedIds = createStore<Set<string>>(new Set())
	.on(fetchFavoriteIdsFx.doneData, (_, ids) => new Set(ids))
	.on(addFavoriteFx.done, (state, { params: id }) => {
		const next = new Set(state);
		next.add(id);
		return next;
	})
	.on(removeFavoriteFx.done, (state, { params: id }) => {
		const next = new Set(state);
		next.delete(id);
		return next;
	})
	.reset(logoutFx.done);
