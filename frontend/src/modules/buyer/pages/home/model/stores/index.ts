import { createStore } from "effector";
import type { UnifiedListingListItem } from "@shared/api/types";
import {
	type SourcedListingListItem,
	unifiedToListItem,
} from "@shared/lib/crawlerAdapter";
import { $searchQuery } from "@modules/buyer/shared/state/model";
import { fetchFeedFx } from "../effects";
import { resetListings, clearFilters } from "../events";
import type { HomeFilters } from "../types";

export const $page = createStore(1).reset(resetListings);

export const $filters = createStore<HomeFilters>({}).reset(clearFilters);

export { $searchQuery };

const $rawItems = createStore<UnifiedListingListItem[]>([]).reset(
	resetListings,
);

export const $total = createStore(0).reset(resetListings);

export const $hasMore = createStore(true).reset(resetListings);

export const $listings = $rawItems.map((items): SourcedListingListItem[] =>
	items.map(unifiedToListItem),
);

export const $isLoading = fetchFeedFx.pending;

export const $error = createStore<string | null>(null).reset(fetchFeedFx);

// Export $rawItems for connections to wire .on() handlers
export { $rawItems };
