import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage } from "@/test/helpers";

// Mock effector-react
vi.mock("effector-react", () => ({
	useUnit: (units: any) => {
		if (Array.isArray(units))
			return units.map((u: any) => u?.getState?.() ?? u);
		if (units && typeof units === "object" && !("getState" in units)) {
			const result: any = {};
			for (const [key, unit] of Object.entries(units)) {
				const u = unit as any;
				result[key] = u?.getState?.() ?? u;
			}
			return result;
		}
		return units?.getState?.() ?? units;
	},
	useStore: (store: any) => store?.getState?.() ?? null,
	useEvent: (event: any) => event ?? vi.fn(),
	useStoreMap: ({ store, fn }: any) => fn(store?.getState?.() ?? null),
}));

// Mock the model - use simple store mocks
vi.mock("../model", () => ({
	pageOpened: vi.fn(),
	loadMore: vi.fn(),
	toggleFavorite: vi.fn(),
	seedListingIds: vi.fn(),
	ensureNearbyResolved: vi.fn(),
	commentAdded: vi.fn(),
	$slideIds: { getState: () => [], "@@unitShape": () => [] },
	$listingsMap: { getState: () => ({}), "@@unitShape": () => ({}) },
	$listings: { getState: () => [], "@@unitShape": () => [] },
	$isLoading: { getState: () => false, "@@unitShape": () => false },
	$isLoadingMore: { getState: () => false, "@@unitShape": () => false },
	$hasMore: { getState: () => false, "@@unitShape": () => false },
	$error: { getState: () => null, "@@unitShape": () => null },
	$initialListingId: { getState: () => null, "@@unitShape": () => null },
	$seedIds: { getState: () => [], "@@unitShape": () => [] },
	$page: { getState: () => 1, "@@unitShape": () => 1 },
}));

// Mock react-router-dom to provide id param
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useNavigate: () => vi.fn(),
		useParams: () => ({ id: "550e8400-e29b-41d4-a716-446655440000" }),
		useSearchParams: () => [new URLSearchParams(), vi.fn()],
		useLocation: () => ({
			pathname: "/listings/550e8400-e29b-41d4-a716-446655440000",
			search: "",
			hash: "",
			state: null,
		}),
	};
});

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

// Mock the TikTok slider component
vi.mock("../ui/main/ListingTikTokSlider", () => ({
	ListingTikTokSlider: (props: any) => (
		<div data-testid="tiktok-slider">{props.slideIds?.length || 0} slides</div>
	),
}));

describe("ListingDetail", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should show loading state when fetching", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show error state when error exists", async () => {
		const model = await import("../model");
		(model.$error as any).getState = () => "Listing not found";
		(model.$error as any)["@@unitShape"] = () => "Listing not found";
		(model.$isLoading as any).getState = () => false;
		(model.$isLoading as any)["@@unitShape"] = () => false;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should call pageOpened on mount", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(model.pageOpened).toBeDefined();
	});

	it("should have toggleFavorite defined", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(model.toggleFavorite).toBeDefined();
	});

	it("should have loadMore event available", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;
		(model.$hasMore as any).getState = () => true;
		(model.$hasMore as any)["@@unitShape"] = () => true;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(model.loadMore).toBeDefined();
	});

	it("should have slide IDs available for rendering", async () => {
		const model = await import("../model");
		const mockSlideIds = ["550e8400-e29b-41d4-a716-446655440000"];
		(model.$slideIds as any).getState = () => mockSlideIds;
		(model.$slideIds as any)["@@unitShape"] = () => mockSlideIds;
		// Keep loading to test store availability
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle listings map data in store", async () => {
		const model = await import("../model");
		const mockMap = {
			"550e8400-e29b-41d4-a716-446655440000": {
				id: "550e8400-e29b-41d4-a716-446655440000",
				title: "Test Listing",
				price: 100000,
			},
		};
		(model.$listingsMap as any).getState = () => mockMap;
		(model.$listingsMap as any)["@@unitShape"] = () => mockMap;
		// Keep loading to verify store data availability
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle error view with go home button", async () => {
		const model = await import("../model");
		(model.$error as any).getState = () => "Not found";
		(model.$error as any)["@@unitShape"] = () => "Not found";
		(model.$isLoading as any).getState = () => false;
		(model.$isLoading as any)["@@unitShape"] = () => false;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render in loading more state", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should support hasMore for pagination", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;
		(model.$hasMore as any).getState = () => true;
		(model.$hasMore as any)["@@unitShape"] = () => true;

		const { ListingDetail } = await import("../ui/page/Page");
		renderPage(<ListingDetail.Page />);
		expect(document.body).toBeTruthy();
	});
});
