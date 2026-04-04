import { sample } from "effector";
import { pageOpened, tabChanged, pageChanged, resetState } from "../events";
import { fetchStatsFx, fetchOLXFx, fetchTelegramFx } from "../effects";
import {
	$stats,
	$activeTab,
	$page,
	$olxListings,
	$telegramListings,
	$totalPages,
	$total,
	$isLoading,
	$error,
} from "../stores";

// --- Store wiring (.on / .reset) ---

$stats.on(fetchStatsFx.doneData, (_, data) => data).reset(resetState);

$activeTab.on(tabChanged, (_, tab) => tab).reset(resetState);

$page.on(pageChanged, (_, p) => p).reset(resetState);

$olxListings.on(fetchOLXFx.doneData, (_, data) => data.items).reset(resetState);

$telegramListings
	.on(fetchTelegramFx.doneData, (_, data) => data.items)
	.reset(resetState);

$totalPages
	.on(fetchOLXFx.doneData, (_, data) => data.total_pages)
	.on(fetchTelegramFx.doneData, (_, data) => data.total_pages)
	.reset(resetState);

$total
	.on(fetchOLXFx.doneData, (_, data) => data.total)
	.on(fetchTelegramFx.doneData, (_, data) => data.total)
	.reset(resetState);

$isLoading
	.on(fetchOLXFx.pending, (_, pending) => pending)
	.on(fetchTelegramFx.pending, (_, pending) => pending)
	.reset(resetState);

$error
	.on(
		fetchStatsFx.failData,
		(_, err) => (err as Error).message || "errors.loadStats",
	)
	.on(
		fetchOLXFx.failData,
		(_, err) => (err as Error).message || "errors.loadListings",
	)
	.on(
		fetchTelegramFx.failData,
		(_, err) => (err as Error).message || "errors.loadListings",
	)
	.on(fetchStatsFx.done, () => null)
	.on(fetchOLXFx.done, () => null)
	.on(fetchTelegramFx.done, () => null)
	.reset(resetState);

// --- Connections (sample) ---

// On page open: fetch stats + first tab
sample({
	clock: pageOpened,
	target: fetchStatsFx,
});

sample({
	clock: pageOpened,
	fn: () => ({ page: 1, per_page: 20 }),
	target: fetchOLXFx,
});

// On tab change: reset page, fetch new tab data
sample({
	clock: tabChanged,
	fn: () => 1,
	target: $page,
});

sample({
	clock: tabChanged,
	filter: (tab) => tab === "olx",
	fn: () => ({ page: 1, per_page: 20 }),
	target: fetchOLXFx,
});

sample({
	clock: tabChanged,
	filter: (tab) => tab === "telegram",
	fn: () => ({ page: 1, per_page: 20 }),
	target: fetchTelegramFx,
});

// On page change: fetch with new page
sample({
	clock: pageChanged,
	source: $activeTab,
	filter: (tab) => tab === "olx",
	fn: (_, page) => ({ page, per_page: 20 }),
	target: fetchOLXFx,
});

sample({
	clock: pageChanged,
	source: $activeTab,
	filter: (tab) => tab === "telegram",
	fn: (_, page) => ({ page, per_page: 20 }),
	target: fetchTelegramFx,
});
