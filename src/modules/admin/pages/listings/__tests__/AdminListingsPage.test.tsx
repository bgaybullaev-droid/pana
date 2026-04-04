import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

// Mock admin shared state
vi.mock("@modules/admin/shared/state", () => ({
	fetchDashboardStats: vi.fn(),
	fetchUsers: vi.fn(),
	fetchUserDetail: vi.fn(),
	approveUser: vi.fn(),
	rejectUser: vi.fn(),
	resetUserDetail: vi.fn(),
	fetchListings: vi.fn(),
	fetchListingDetail: vi.fn(),
	approveListing: vi.fn(),
	rejectListing: vi.fn(),
	resetListingDetail: vi.fn(),
	approveUserFx: { done: { watch: vi.fn(() => vi.fn()) } },
	rejectUserFx: { done: { watch: vi.fn(() => vi.fn()) } },
	approveListingFx: { done: { watch: vi.fn(() => vi.fn()) } },
	rejectListingFx: { done: { watch: vi.fn(() => vi.fn()) } },
	$dashboardStats: { getState: () => null, "@@unitShape": () => null },
	$isLoadingDashboard: { getState: () => false, "@@unitShape": () => false },
	$users: { getState: () => [], "@@unitShape": () => [] },
	$usersPagination: {
		getState: () => ({ total: 0, page: 1, per_page: 20, totalPages: 0 }),
		"@@unitShape": () => ({ total: 0, page: 1, per_page: 20, totalPages: 0 }),
	},
	$isLoadingUsers: { getState: () => false, "@@unitShape": () => false },
	$selectedUser: { getState: () => null, "@@unitShape": () => null },
	$isLoadingUserDetail: { getState: () => false, "@@unitShape": () => false },
	$listings: { getState: () => [], "@@unitShape": () => [] },
	$listingsPagination: {
		getState: () => ({ total: 0, page: 1, per_page: 20, totalPages: 0 }),
		"@@unitShape": () => ({ total: 0, page: 1, per_page: 20, totalPages: 0 }),
	},
	$isLoadingListings: { getState: () => false, "@@unitShape": () => false },
	$selectedListing: { getState: () => null, "@@unitShape": () => null },
	$isLoadingListingDetail: {
		getState: () => false,
		"@@unitShape": () => false,
	},
	$adminError: { getState: () => null, "@@unitShape": () => null },
}));

// Mock effector-react
vi.mock("effector-react", () => ({
	useUnit: (units: any) => {
		if (Array.isArray(units))
			return units.map((u: any) =>
				typeof u?.getState === "function" ? u.getState() : u,
			);
		return typeof units?.getState === "function" ? units.getState() : units;
	},
	useStore: (store: any) => store?.getState?.() ?? null,
	useEvent: (event: any) => event ?? vi.fn(),
}));

// Mock react-i18next
vi.mock("react-i18next", () => ({
	useTranslation: () => ({
		t: (key: string, opts?: any) => {
			const map: Record<string, string> = {
				"listings.title": "Listings",
				"listings.subtitle": "Manage property listings",
				"listings.searchPlaceholder": "Search listings...",
				"listings.noListingsFound": "No listings found",
				"listings.manual": "Manual",
				"listings.claimed": "Claimed",
				"listings.parsed": "Parsed",
				"common.all": "All",
				"common.pending": "Pending",
				"common.approved": "Approved",
				"common.rejected": "Rejected",
				"common.allSources": "All Sources",
				"common.tryAdjustingFilters": "Try adjusting your filters",
			};
			if (key === "listings.showing" && opts)
				return `Showing ${opts.count} of ${opts.total}`;
			return map[key] || key;
		},
		i18n: { language: "en" },
	}),
}));

// Mock formatPrice
vi.mock("@app/styles/theme", () => ({
	formatPrice: (price: number, _currency: string) => `$${price}`,
}));

// Mock regions
vi.mock("@shared/lib/regions", () => ({
	translateDistrict: (key: string) => key,
}));

// Mock CSS
vi.mock("@modules/admin/shared/ui/admin.css", () => ({}));

describe("AdminListings", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeleton when isLoading is true", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$isLoadingListings as any).getState = () => true;
		(state.$isLoadingListings as any)["@@unitShape"] = () => true;

		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(document.querySelector(".admin-skeleton-card")).toBeTruthy();
	});

	it("should display listings when data exists", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListings = [
			{
				id: "1",
				title: "Nice Apartment",
				price: 50000,
				currency: "USD",
				property_type: "apartment",
				type: "sell",
				moderation_status: "pending",
				source_type: "manual",
				primary_image_url: null,
				district: "chilanzar",
				seller_name: "John",
				images: [],
			},
			{
				id: "2",
				title: "Cozy House",
				price: 80000,
				currency: "USD",
				property_type: "house",
				type: "sell",
				moderation_status: "approved",
				source_type: "claimed",
				primary_image_url: null,
				district: "yunusabad",
				seller_name: "Jane",
				images: [],
			},
		];
		(state.$listings as any).getState = () => mockListings;
		(state.$listings as any)["@@unitShape"] = () => mockListings;
		(state.$isLoadingListings as any).getState = () => false;
		(state.$isLoadingListings as any)["@@unitShape"] = () => false;
		const pag = { total: 2, page: 1, per_page: 20, totalPages: 1 };
		(state.$listingsPagination as any).getState = () => pag;
		(state.$listingsPagination as any)["@@unitShape"] = () => pag;

		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(screen.getByText("Nice Apartment")).toBeTruthy();
		expect(screen.getByText("Cozy House")).toBeTruthy();
	});

	it("should render moderation status chip filters", async () => {
		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(screen.getByText("All")).toBeTruthy();
		expect(screen.getByText("Pending")).toBeTruthy();
		expect(screen.getByText("Approved")).toBeTruthy();
		expect(screen.getByText("Rejected")).toBeTruthy();
	});

	it("should render source type chip filters", async () => {
		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(screen.getByText("All Sources")).toBeTruthy();
		expect(screen.getByText("Manual")).toBeTruthy();
		expect(screen.getByText("Claimed")).toBeTruthy();
		expect(screen.getByText("Parsed")).toBeTruthy();
	});

	it("should display search input", async () => {
		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(screen.getByPlaceholderText("Search listings...")).toBeTruthy();
	});

	it("should show empty state when no listings", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$listings as any).getState = () => [];
		(state.$listings as any)["@@unitShape"] = () => [];
		(state.$isLoadingListings as any).getState = () => false;
		(state.$isLoadingListings as any)["@@unitShape"] = () => false;

		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(screen.getByText("No listings found")).toBeTruthy();
	});

	it("should display page title and subtitle", async () => {
		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(screen.getByText("Listings")).toBeTruthy();
		expect(screen.getByText("Manage property listings")).toBeTruthy();
	});

	it("should display moderation status badges on listing cards", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListings = [
			{
				id: "1",
				title: "Test",
				price: 100,
				currency: "USD",
				property_type: "apartment",
				type: "sell",
				moderation_status: "pending",
				source_type: "manual",
				primary_image_url: null,
				district: "",
				seller_name: "",
				images: [],
			},
		];
		(state.$listings as any).getState = () => mockListings;
		(state.$listings as any)["@@unitShape"] = () => mockListings;
		(state.$isLoadingListings as any).getState = () => false;
		(state.$isLoadingListings as any)["@@unitShape"] = () => false;
		const pag = { total: 1, page: 1, per_page: 20, totalPages: 1 };
		(state.$listingsPagination as any).getState = () => pag;
		(state.$listingsPagination as any)["@@unitShape"] = () => pag;

		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(screen.getByText("pending")).toBeTruthy();
		expect(screen.getByText("manual")).toBeTruthy();
	});

	it("should display total count badge when listings exist", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$listings as any).getState = () => [
			{
				id: "1",
				title: "Test",
				price: 100,
				currency: "USD",
				property_type: "apartment",
				type: "sell",
				moderation_status: "pending",
				source_type: "manual",
				primary_image_url: null,
				district: "",
				seller_name: "",
				images: [],
			},
		];
		(state.$listings as any)["@@unitShape"] = () => [
			{
				id: "1",
				title: "Test",
				price: 100,
				currency: "USD",
				property_type: "apartment",
				type: "sell",
				moderation_status: "pending",
				source_type: "manual",
				primary_image_url: null,
				district: "",
				seller_name: "",
				images: [],
			},
		];
		(state.$isLoadingListings as any).getState = () => false;
		(state.$isLoadingListings as any)["@@unitShape"] = () => false;
		const pag = { total: 42, page: 1, per_page: 20, totalPages: 3 };
		(state.$listingsPagination as any).getState = () => pag;
		(state.$listingsPagination as any)["@@unitShape"] = () => pag;

		const { AdminListings } = await import("../ui/page/Page");
		renderPage(<AdminListings.Page />);
		expect(screen.getByText("42")).toBeTruthy();
	});
});
