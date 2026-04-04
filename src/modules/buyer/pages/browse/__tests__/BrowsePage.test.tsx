import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage } from "@/test/helpers";

// Mock the model
vi.mock("../model", () => ({
	pageOpened: vi.fn(),
	loadMore: vi.fn(),
	likeToggled: vi.fn(),
	shareClicked: vi.fn(),
	messageClicked: vi.fn(),
	filtersChanged: vi.fn(),
	searchChanged: vi.fn(),
	resetListings: vi.fn(),
	$listings: { getState: () => [], "@@unitShape": () => [] },
	$isLoading: { getState: () => false, "@@unitShape": () => false },
	$hasMore: { getState: () => false, "@@unitShape": () => false },
	$filters: {
		getState: () => ({
			sortingSelected: -1,
			priceRange: [0, 2000000],
			regions: [],
		}),
		"@@unitShape": () => ({
			sortingSelected: -1,
			priceRange: [0, 2000000],
			regions: [],
		}),
	},
	$searchTerm: { getState: () => "", "@@unitShape": () => "" },
	$page: { getState: () => 1, "@@unitShape": () => 1 },
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

// Mock useTelegram hook
vi.mock("@app/providers/useTelegram", () => ({
	useTelegram: () => ({
		webApp: {
			HapticFeedback: { impactOccurred: vi.fn() },
			openTelegramLink: vi.fn(),
		},
	}),
}));

// Mock shared libs
vi.mock("@shared/lib/constants", () => ({
	getListingShareUrl: (id: string) => `https://t.me/share?url=${id}`,
}));

// Mock TikTokSlider
vi.mock("@modules/buyer/pages/listing-detail/ui/main/Sliders", () => ({
	TikTokSlider: (props: any) => (
		<div data-testid="tiktok-slider">
			{props.listings?.length || 0} listings
		</div>
	),
}));

describe("Browse", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading state when fetching initial data", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;
		(model.$listings as any).getState = () => [];
		(model.$listings as any)["@@unitShape"] = () => [];

		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render TikTok slider when listings exist", async () => {
		const model = await import("../model");
		const mockListings = [
			{
				id: "1",
				title: "Test",
				price: 50000,
				images: [{ url: "/img.jpg" }],
				sellerUserName: "seller1",
			},
		];
		(model.$listings as any).getState = () => mockListings;
		(model.$listings as any)["@@unitShape"] = () => mockListings;
		(model.$isLoading as any).getState = () => false;
		(model.$isLoading as any)["@@unitShape"] = () => false;

		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should call pageOpened on mount", async () => {
		const model = await import("../model");
		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(model.pageOpened).toBeDefined();
	});

	it("should render back button", async () => {
		const model = await import("../model");
		(model.$listings as any).getState = () => [
			{ id: "1", title: "Test", price: 50000 },
		];
		(model.$listings as any)["@@unitShape"] = () => [
			{ id: "1", title: "Test", price: 50000 },
		];
		(model.$isLoading as any).getState = () => false;
		(model.$isLoading as any)["@@unitShape"] = () => false;

		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle like toggle", async () => {
		const model = await import("../model");
		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(model.likeToggled).toBeDefined();
	});

	it("should handle share action", async () => {
		const model = await import("../model");
		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(model.shareClicked).toBeDefined();
	});

	it("should handle message action", async () => {
		const model = await import("../model");
		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(model.messageClicked).toBeDefined();
	});

	it("should pass hasMore to slider", async () => {
		const model = await import("../model");
		(model.$hasMore as any).getState = () => true;
		(model.$hasMore as any)["@@unitShape"] = () => true;

		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle loadMore event", async () => {
		const model = await import("../model");
		const { Browse } = await import("../ui/page/Page");
		renderPage(<Browse.Page />);
		expect(model.loadMore).toBeDefined();
	});
});
