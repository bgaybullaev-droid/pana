import { createEvent, sample } from "effector";
import { getApiError } from "@shared/api/client";
import type { UnifiedListing } from "@shared/api/types";
import {
	addFavoriteFx,
	removeFavoriteFx,
} from "@modules/buyer/shared/state/model";
import { onContentLanguageChanged } from "@shared/i18n";
import {
	fetchInitialListingFx,
	fetchFeedFx,
	fetchListingDetailsFx,
	_inflight,
} from "../effects";
import {
	pageOpened,
	loadMore,
	toggleFavorite,
	commentAdded,
	ensureNearbyResolved,
} from "../events";
import {
	$seedIds,
	$seedSource,
	$initialListingId,
	$listingsMap,
	$listings,
	$page,
	$hasMore,
	$isLoadingMore,
	$error,
} from "../stores";
import { PREFETCH_WINDOW } from "../lib";

// Wire .on() handlers
// Note: $seedIds and $seedSource are shared stores with .on() handlers
// already wired in @modules/buyer/shared/state/model/stores

$initialListingId.on(pageOpened, (_, id) => id);

$listingsMap
	.on(fetchInitialListingFx.doneData, (state, listing) => ({
		...state,
		[listing.id]: listing,
	}))
	.on(fetchListingDetailsFx.doneData, (state, newListings) => {
		if (newListings.length === 0) return state;
		const updated = { ...state };
		for (const l of newListings) {
			updated[l.id] = l;
		}
		return updated;
	})
	.on(addFavoriteFx.done, (state, { params: listingId }) => {
		const listing = state[listingId];
		if (!listing) return state;
		return {
			...state,
			[listingId]: {
				...listing,
				is_favorited: true,
				favorites_count: listing.favorites_count + 1,
			},
		};
	})
	.on(removeFavoriteFx.done, (state, { params: listingId }) => {
		const listing = state[listingId];
		if (!listing) return state;
		return {
			...state,
			[listingId]: {
				...listing,
				is_favorited: false,
				favorites_count: Math.max(0, listing.favorites_count - 1),
			},
		};
	})
	.on(commentAdded, (state, listingId) => {
		const listing = state[listingId];
		if (!listing) return state;
		return {
			...state,
			[listingId]: { ...listing, comments_count: listing.comments_count + 1 },
		};
	});

$page.on(fetchFeedFx.done, (_, { params }) => params.page + 1);

$hasMore.on(fetchFeedFx.doneData, (_, data) => data.page < data.total_pages);

$error.on(
	fetchInitialListingFx.failData,
	(_, error) => getApiError(error).message,
);

// Fetch initial listing on page open
sample({
	clock: pageOpened,
	target: fetchInitialListingFx,
});

// On-demand fetching: when the visible slide changes, resolve only the
// nearby IDs that are not already in the store (or in-flight).
sample({
	clock: ensureNearbyResolved,
	source: { seedIds: $seedIds, listingsMap: $listingsMap },
	fn: ({ seedIds, listingsMap }, visibleId) => {
		if (seedIds.length === 0) return [];
		const seedIndex = seedIds.indexOf(visibleId);
		if (seedIndex < 0) return [];
		const start = Math.max(0, seedIndex - PREFETCH_WINDOW);
		const end = Math.min(seedIds.length, seedIndex + PREFETCH_WINDOW + 1);
		const nearby = seedIds.slice(start, end);
		// Only fetch IDs not already resolved and not currently in-flight
		return nearby.filter((id) => !(id in listingsMap) && !_inflight.has(id));
	},
	target: fetchListingDetailsFx,
});

// If NOT seeded, fall back to generic feed
sample({
	clock: fetchInitialListingFx.done,
	source: { seedIds: $seedIds, initialId: $initialListingId },
	filter: ({ seedIds }) => seedIds.length === 0,
	fn: ({ initialId }) => ({ page: 1, exclude_id: initialId || undefined }),
	target: fetchFeedFx,
});

// Append generic feed IDs to seed list so they appear in order.
// Actual detail fetching happens on-demand via ensureNearbyResolved
// when the user scrolls near them — no bulk fetch here.
$seedIds.on(fetchFeedFx.doneData, (state, data) => {
	const existing = new Set(state);
	const newIds = data.items
		.map((item) => item.id)
		.filter((id) => !existing.has(id));
	return [...state, ...newIds];
});

// Load more — disabled when seeds come from a finite source (e.g. Favorites).
// The home feed seeds hundreds of IDs and expects pagination to continue;
// Favorites seeds only the user's favorites and should not grow.
sample({
	clock: loadMore,
	source: {
		page: $page,
		hasMore: $hasMore,
		isLoading: $isLoadingMore,
		initialId: $initialListingId,
		seedSource: $seedSource,
	},
	filter: ({ hasMore, isLoading, seedSource }) =>
		hasMore && !isLoading && seedSource !== "finite",
	fn: ({ page, initialId }) => ({ page, exclude_id: initialId || undefined }),
	target: fetchFeedFx,
});

// Toggle favorite: add if not favorited
sample({
	clock: toggleFavorite,
	source: $listings,
	filter: (listings: UnifiedListing[], id: string) => {
		const listing = listings.find((l) => l.id === id);
		return listing !== undefined && listing.is_favorited === false;
	},
	fn: (_: UnifiedListing[], id: string) => id,
	target: addFavoriteFx,
});

// Toggle favorite: remove if already favorited
sample({
	clock: toggleFavorite,
	source: $listings,
	filter: (listings: UnifiedListing[], id: string) => {
		const listing = listings.find((l) => l.id === id);
		return listing !== undefined && listing.is_favorited === true;
	},
	fn: (_: UnifiedListing[], id: string) => id,
	target: removeFavoriteFx,
});

// Re-fetch current listing when content language changes
const contentLanguageChanged = createEvent();
onContentLanguageChanged(() => contentLanguageChanged());

sample({
	clock: contentLanguageChanged,
	source: $initialListingId,
	filter: (id): id is string => id !== null,
	target: fetchInitialListingFx,
});
