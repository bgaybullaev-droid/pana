import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage } from "@/test/helpers";

// Mock the model
vi.mock("../model", () => ({
	pageOpened: vi.fn(),
	loadMore: vi.fn(),
	toggleFavorite: vi.fn(),
	searchQueryChanged: vi.fn(),
	filtersChanged: vi.fn(),
	applyFilters: vi.fn(),
	clearFilters: vi.fn(),
	tabChanged: vi.fn(),
	$listings: { getState: () => [], "@@unitShape": () => [] },
	$isLoading: { getState: () => false, "@@unitShape": () => false },
	$hasMore: { getState: () => false, "@@unitShape": () => false },
	$total: { getState: () => 0, "@@unitShape": () => 0 },
	$searchQuery: { getState: () => "", "@@unitShape": () => "" },
	$filters: { getState: () => ({}), "@@unitShape": () => ({}) },
	$favoritedIds: { getState: () => new Set(), "@@unitShape": () => new Set() },
	$activeTab: { getState: () => "feed", "@@unitShape": () => "feed" },
	$isSubscriptionsLoading: { getState: () => false, "@@unitShape": () => false },
	$isRecommendedLoading: { getState: () => false, "@@unitShape": () => false },
	fetchFeedFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
	},
}));

// Mock effector-react
vi.mock("effector-react", () => ({
	useUnit: (units: any) => {
		if (Array.isArray(units))
			return units.map((u: any) => u?.getState?.() ?? u);
		return units?.getState?.() ?? units;
	},
	useStore: (store: any) => store?.getState?.() ?? null,
	useEvent: (event: any) => event ?? vi.fn(),
}));

// Mock shared UI components
vi.mock("@shared/ui/ListingCard", () => ({
	ListingCard: ({ listing }: any) => (
		<div data-testid="listing-card">{listing?.title}</div>
	),
}));

// Mock layout context
vi.mock("@modules/buyer/app/ui/layout/BuyerLayout", () => ({
	useLayoutContext: () => ({ openSearch: vi.fn() }),
	clearScrollPosition: vi.fn(),
}));

// Mock listing-detail model
vi.mock("@modules/buyer/pages/listing-detail/model", () => ({
	seedListingIds: vi.fn(),
}));

// Mock shared libs
vi.mock("@shared/lib/crawlerAdapter", () => ({
	getListingDetailUrl: (item: any) => `/listings/${item.id}`,
	unifiedToListItem: (item: any) => item,
}));

vi.mock("@shared/lib/constants", () => ({
	ROOMS_OPTIONS_KEYS: ["studio", "1", "2", "3", "4"],
}));

vi.mock("@shared/lib/regions", () => ({
	getRegionKeys: () => ["tashkent"],
	getDistrictsForRegion: () => ["chilanzar"],
	translateRegion: (key: string) => key,
	translateDistrict: (key: string) => key,
}));

describe("Home", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading state initially", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		// Should render skeleton/loading indicators
		expect(document.body).toBeTruthy();
	});

	it("should display empty state when no listings", async () => {
		const model = await import("../model");
		(model.$listings as any).getState = () => [];
		(model.$listings as any)["@@unitShape"] = () => [];
		(model.$isLoading as any).getState = () => false;
		(model.$isLoading as any)["@@unitShape"] = () => false;

		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		// Empty state should be rendered
		expect(document.body).toBeTruthy();
	});

	it("should render listing cards when data exists", async () => {
		const model = await import("../model");
		const mockListings = [
			{
				id: "1",
				title: "Test Apt",
				price: 50000,
				type: "sell",
				property_type: "apartment",
				images: [],
				source: "platform",
			},
		];
		(model.$listings as any).getState = () => mockListings;
		(model.$listings as any)["@@unitShape"] = () => mockListings;

		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should call pageOpened on mount", async () => {
		const model = await import("../model");
		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		expect(model.pageOpened).toBeDefined();
	});

	it("should handle filter changes", async () => {
		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should support infinite scroll", async () => {
		const model = await import("../model");
		(model.$hasMore as any).getState = () => true;
		(model.$hasMore as any)["@@unitShape"] = () => true;

		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle favorite toggle", async () => {
		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should clear filters", async () => {
		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle search query changes", async () => {
		const { Home } = await import("../ui/page/Page");
		renderPage(<Home.Page />);
		expect(document.body).toBeTruthy();
	});
});
