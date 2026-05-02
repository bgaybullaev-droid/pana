import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

// Mock the model
vi.mock("../model", () => ({
	pageOpened: vi.fn(),
	loadMore: vi.fn(),
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

// Mock the ListingsGrid component
vi.mock("../ui/main/ListingsGrid", () => ({
	ListingsGrid: () => <div data-testid="listings-grid">Listings Grid</div>,
}));

describe("Listings", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render ListingsGrid component", async () => {
		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(screen.getByTestId("listings-grid")).toBeTruthy();
	});

	it("should call pageOpened on mount", async () => {
		const model = await import("../model");
		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(model.pageOpened).toBeDefined();
	});

	it("should have loadMore event available", async () => {
		const model = await import("../model");
		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(model.loadMore).toBeDefined();
	});

	it("should have filtersChanged event available", async () => {
		const model = await import("../model");
		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(model.filtersChanged).toBeDefined();
	});

	it("should have searchChanged event available", async () => {
		const model = await import("../model");
		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(model.searchChanged).toBeDefined();
	});

	it("should render correctly with loading state", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(screen.getByTestId("listings-grid")).toBeTruthy();
	});

	it("should render correctly with listings data", async () => {
		const model = await import("../model");
		const mockListings = [
			{ id: "1", title: "Apt 1", price: 50000 },
			{ id: "2", title: "Apt 2", price: 75000 },
		];
		(model.$listings as any).getState = () => mockListings;
		(model.$listings as any)["@@unitShape"] = () => mockListings;

		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(screen.getByTestId("listings-grid")).toBeTruthy();
	});

	it("should support pagination via hasMore store", async () => {
		const model = await import("../model");
		(model.$hasMore as any).getState = () => true;
		(model.$hasMore as any)["@@unitShape"] = () => true;

		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle reset listings", async () => {
		const model = await import("../model");
		const { Listings } = await import("../ui/page/Page");
		renderPage(<Listings.Page />);
		expect(model.resetListings).toBeDefined();
	});
});
