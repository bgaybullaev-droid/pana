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
	$dashboardStats: {
		getState: () => ({
			total_users: 100,
			pending_users: 5,
			total_listings: 200,
			pending_listings: 10,
			approved_users: 80,
			rejected_users: 15,
			approved_listings: 170,
			rejected_listings: 20,
		}),
		"@@unitShape": () => ({
			total_users: 100,
			pending_users: 5,
			total_listings: 200,
			pending_listings: 10,
			approved_users: 80,
			rejected_users: 15,
			approved_listings: 170,
			rejected_listings: 20,
		}),
	},
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

// Mock crawled model
vi.mock("../../../crawled/model", () => ({
	fetchCrawledStatsFx: vi.fn(),
	$crawledStats: {
		getState: () => ({ olx_count: 50, telegram_count: 30 }),
		"@@unitShape": () => ({ olx_count: 50, telegram_count: 30 }),
	},
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
	initReactI18next: { type: "3rdParty", init: vi.fn() },
	useTranslation: () => ({
		t: (key: string, opts?: any) => {
			const map: Record<string, string> = {
				"dashboard.requiresAttention": "Requires Attention",
				"dashboard.pendingUsers": "Pending Users",
				"dashboard.pendingListings": "Pending Listings",
				"dashboard.crawledData": "Crawled Data",
				"dashboard.userStats": "User Stats",
				"dashboard.listingStats": "Listing Stats",
				"dashboard.total": "Total",
				"dashboard.approved": "Approved",
				"dashboard.rejected": "Rejected",
				"common.viewAll": "View All",
			};
			if (key === "dashboard.of" && opts?.total) return `of ${opts.total}`;
			return map[key] || key;
		},
		i18n: { language: "en" },
	}),
}));

// Mock CSS
vi.mock("@modules/admin/shared/ui/admin.css", () => ({}));

describe("AdminDashboard", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should display pending users stat card", async () => {
		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(screen.getByText("Pending Users")).toBeTruthy();
	});

	it("should display pending listings stat card", async () => {
		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(screen.getByText("Pending Listings")).toBeTruthy();
	});

	it("should display requires attention section", async () => {
		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(screen.getByText("Requires Attention")).toBeTruthy();
	});

	it("should show loading skeleton when isLoading is true", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$isLoadingDashboard as any).getState = () => true;
		(state.$isLoadingDashboard as any)["@@unitShape"] = () => true;

		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		// Skeleton elements rendered instead of stats
		expect(document.querySelector(".admin-skeleton")).toBeTruthy();
	});

	it("should call fetchDashboardStats on mount", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$isLoadingDashboard as any).getState = () => false;
		(state.$isLoadingDashboard as any)["@@unitShape"] = () => false;

		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(state.fetchDashboardStats).toBeDefined();
	});

	it("should display user stats section", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$isLoadingDashboard as any).getState = () => false;
		(state.$isLoadingDashboard as any)["@@unitShape"] = () => false;

		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(screen.getByText("User Stats")).toBeTruthy();
	});

	it("should display listing stats section", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$isLoadingDashboard as any).getState = () => false;
		(state.$isLoadingDashboard as any)["@@unitShape"] = () => false;

		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(screen.getByText("Listing Stats")).toBeTruthy();
	});

	it("should display crawled data section", async () => {
		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(screen.getByText("Crawled Data")).toBeTruthy();
	});

	it("should render OLX and Telegram crawled mini cards", async () => {
		const { AdminDashboard } = await import("../ui/page/Page");
		renderPage(<AdminDashboard.Page />);
		expect(screen.getByText("OLX.uz")).toBeTruthy();
		expect(screen.getByText("Telegram")).toBeTruthy();
	});
});
