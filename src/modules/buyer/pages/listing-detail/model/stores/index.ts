import { createStore, combine } from "effector";
import type { UnifiedListing } from "@shared/api/types";
import { fetchInitialListingFx, fetchListingDetailsFx } from "../effects";
import {
	$sharedSeedIds,
	$sharedSeedSource,
} from "@modules/buyer/shared/state/model";

// Re-export shared seed stores so existing imports still work
export const $seedIds = $sharedSeedIds;
export const $seedSource = $sharedSeedSource;

export const $initialListingId = createStore<string | null>(null);

// Map of resolved listings (keyed by ID)
export const $listingsMap = createStore<Record<string, UnifiedListing>>({});

// All slide IDs in display order — includes unresolved IDs so the slider
// can render placeholders and the user can scroll to trigger on-demand fetching.
export const $slideIds = combine(
	$seedIds,
	$listingsMap,
	$initialListingId,
	(seedIds, listingsMap, initialId) => {
		if (seedIds.length > 0) {
			// Ensure initial listing is in the list (non-seeded path: feed excludes it)
			if (initialId && !seedIds.includes(initialId)) {
				return [initialId, ...seedIds];
			}
			return seedIds;
		}
		// No seeds yet: resolved IDs, ensuring initial is first
		const keys = Object.keys(listingsMap);
		if (initialId && !keys.includes(initialId)) {
			return [initialId, ...keys];
		}
		return keys;
	},
);

// Resolved listings only — used by toggle-favorite logic
export const $listings = combine(
	$seedIds,
	$listingsMap,
	(seedIds, listingsMap): UnifiedListing[] => {
		if (seedIds.length > 0) {
			return seedIds
				.filter((id) => id in listingsMap)
				.map((id) => listingsMap[id]);
		}
		return Object.values(listingsMap);
	},
);

export const $page = createStore(1);

export const $hasMore = createStore(true);

export const $isLoading = fetchInitialListingFx.pending;
export const $isLoadingMore = fetchListingDetailsFx.pending;

export const $error = createStore<string | null>(null).reset(
	fetchInitialListingFx,
);
