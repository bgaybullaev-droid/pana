import { combine, createStore } from "effector";
import type {
	ListingListItem,
	UnifiedListingListItem,
} from "@shared/api/types";
import {
	type SourcedListingListItem,
	mainToListItem,
	unifiedToListItem,
} from "@shared/lib/crawlerAdapter";
import { $searchQuery } from "@modules/buyer/shared/state/model";
import {
	fetchFeedFx,
	fetchRecommendedFeedFx,
	fetchSubscriptionsFeedFx,
} from "../effects";
import { resetListings, clearFilters, tabChanged } from "../events";
import type { HomeFilters, HomeTab } from "../types";

export const $page = createStore(1).reset(resetListings);

export const $filters = createStore<HomeFilters>({}).reset(clearFilters);

export { $searchQuery };

const $rawItems = createStore<UnifiedListingListItem[]>([]).reset(
	resetListings,
);

export const $total = createStore(0).reset(resetListings);

export const $hasMore = createStore(true).reset(resetListings);

// F048 — active home tab. Defaults to the legacy feed so existing buyer
// behavior is unchanged for users who never tap a tab.
export const $activeTab = createStore<HomeTab>("feed").on(
	tabChanged,
	(_, next) => next,
);

// Subscriptions tab — flat ListingListItem rows from /buyer/feed/subscriptions.
export const $subscriptionsItems = createStore<ListingListItem[]>([]).on(
	fetchSubscriptionsFeedFx.doneData,
	(_, res) => res.items,
);

// Recommended tab — flat ListingListItem rows from /buyer/feed/recommended.
export const $recommendedItems = createStore<ListingListItem[]>([]).on(
	fetchRecommendedFeedFx.doneData,
	(_, res) => res.items,
);

const $feedListings = $rawItems.map((items): SourcedListingListItem[] =>
	items.map(unifiedToListItem),
);

const $subscriptionListings = $subscriptionsItems.map(
	(items): SourcedListingListItem[] => items.map(mainToListItem),
);

const $recommendedListings = $recommendedItems.map(
	(items): SourcedListingListItem[] => items.map(mainToListItem),
);

// `$listings` is the view-active list. Tab change swaps the underlying
// source without touching the consumer. Pagination ("load more") only
// applies to the feed tab — subscriptions and recommended are single-shot.
export const $listings = combine(
	$activeTab,
	$feedListings,
	$subscriptionListings,
	$recommendedListings,
	(tab, feed, subs, rec) => {
		if (tab === "subscriptions") return subs;
		if (tab === "recommended") return rec;
		return feed;
	},
);

export const $isLoading = fetchFeedFx.pending;
export const $isSubscriptionsLoading = fetchSubscriptionsFeedFx.pending;
export const $isRecommendedLoading = fetchRecommendedFeedFx.pending;

export const $error = createStore<string | null>(null).reset(fetchFeedFx);

// Export $rawItems for connections to wire .on() handlers
export { $rawItems, $feedListings, $subscriptionListings, $recommendedListings };
