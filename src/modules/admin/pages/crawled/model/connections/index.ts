import { sample } from "effector";
import {
	pageOpened,
	sourceChanged,
	pageChanged,
	propertyTypeChanged,
	listingTypeChanged,
	resetCrawledState,
} from "../events";
import { fetchOLXFx, fetchTelegramFx, fetchCrawledStatsFx } from "../effects";
import {
	$crawledStats,
	$activeSource,
	$crawledPage,
	$propertyType,
	$listingType,
	$olxListings,
	$telegramListings,
	$olxTotal,
	$telegramTotal,
	$olxTotalPages,
	$telegramTotalPages,
	$isLoadingCrawled,
	$crawledError,
} from "../stores";
import { buildFilters } from "../lib";

// Store .on() wiring
$crawledStats
	.on(fetchCrawledStatsFx.doneData, (_, data) => data)
	.reset(resetCrawledState);

$activeSource.on(sourceChanged, (_, source) => source).reset(resetCrawledState);

$crawledPage.on(pageChanged, (_, p) => p).reset(resetCrawledState);

$propertyType.on(propertyTypeChanged, (_, v) => v).reset(resetCrawledState);

$listingType.on(listingTypeChanged, (_, v) => v).reset(resetCrawledState);

$olxListings
	.on(fetchOLXFx.doneData, (_, data) => data.items)
	.reset(resetCrawledState);

$telegramListings
	.on(fetchTelegramFx.doneData, (_, data) => data.items)
	.reset(resetCrawledState);

$olxTotal
	.on(fetchOLXFx.doneData, (_, data) => data.total)
	.reset(resetCrawledState);

$telegramTotal
	.on(fetchTelegramFx.doneData, (_, data) => data.total)
	.reset(resetCrawledState);

$olxTotalPages
	.on(fetchOLXFx.doneData, (_, data) => data.total_pages)
	.reset(resetCrawledState);

$telegramTotalPages
	.on(fetchTelegramFx.doneData, (_, data) => data.total_pages)
	.reset(resetCrawledState);

$isLoadingCrawled
	.on(fetchOLXFx.pending, (_, pending) => pending)
	.on(fetchTelegramFx.pending, (_, pending) => pending)
	.reset(resetCrawledState);

$crawledError
	.on(
		fetchOLXFx.failData,
		(_, err) => (err as Error).message || "errors.loadOlx",
	)
	.on(
		fetchTelegramFx.failData,
		(_, err) => (err as Error).message || "errors.loadTelegram",
	)
	.on(
		fetchCrawledStatsFx.failData,
		(_, err) => (err as Error).message || "errors.loadStats",
	)
	.on(fetchOLXFx.done, () => null)
	.on(fetchTelegramFx.done, () => null)
	.reset(resetCrawledState);

// Sample connections

// On page open: fetch stats
sample({
	clock: pageOpened,
	target: fetchCrawledStatsFx,
});

// On page open: fetch both sources
sample({
	clock: pageOpened,
	source: {
		page: $crawledPage,
		propertyType: $propertyType,
		listingType: $listingType,
	},
	fn: (s) => buildFilters(s),
	target: fetchOLXFx,
});

sample({
	clock: pageOpened,
	source: {
		page: $crawledPage,
		propertyType: $propertyType,
		listingType: $listingType,
	},
	fn: (s) => buildFilters(s),
	target: fetchTelegramFx,
});

// On source change: reset page to 1
sample({
	clock: sourceChanged,
	fn: () => 1,
	target: $crawledPage,
});

// On source/page/filter change: refetch relevant data
const $allFilters = sample({
	clock: [sourceChanged, pageChanged, propertyTypeChanged, listingTypeChanged],
	source: {
		source: $activeSource,
		page: $crawledPage,
		propertyType: $propertyType,
		listingType: $listingType,
	},
});

sample({
	clock: $allFilters,
	filter: ({ source }) => source === "all" || source === "olx",
	fn: ({ page, propertyType, listingType }) =>
		buildFilters({ page, propertyType, listingType }),
	target: fetchOLXFx,
});

sample({
	clock: $allFilters,
	filter: ({ source }) => source === "all" || source === "telegram",
	fn: ({ page, propertyType, listingType }) =>
		buildFilters({ page, propertyType, listingType }),
	target: fetchTelegramFx,
});
