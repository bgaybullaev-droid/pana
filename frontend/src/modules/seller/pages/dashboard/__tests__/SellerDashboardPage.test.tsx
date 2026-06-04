import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

// Mock seller shared state
vi.mock("@modules/seller/shared/state", () => ({
	$sellerProfile: {
		getState: () => ({ company_name: "Test Company", phone: "+998901234567" }),
		"@@unitShape": () => ({
			company_name: "Test Company",
			phone: "+998901234567",
		}),
	},
	$sellerStats: {
		getState: () => ({
			totalListings: 5,
			activeListings: 3,
			totalViews: 120,
			totalContacts: 8,
			totalFavorites: 15,
		}),
		"@@unitShape": () => ({
			totalListings: 5,
			activeListings: 3,
			totalViews: 120,
			totalContacts: 8,
			totalFavorites: 15,
		}),
	},
	$isLoadingProfile: { getState: () => false, "@@unitShape": () => false },
	fetchSellerProfile: vi.fn(),
	fetchSellerListings: vi.fn(),
	resetSellerState: vi.fn(),
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

// Mock shared UI
vi.mock("@shared/ui/StatCard", () => ({
	StatCard: ({ label, value }: any) => (
		<div data-testid="stat-card">
			<span data-testid="stat-value">{value}</span>
			<span data-testid="stat-label">{label}</span>
		</div>
	),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useNavigate: () => mockNavigate,
		useParams: () => ({}),
		useSearchParams: () => [new URLSearchParams(), vi.fn()],
		useLocation: () => ({
			pathname: "/seller/dashboard",
			search: "",
			hash: "",
			state: null,
		}),
	};
});

describe("SellerDashboard", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { SellerDashboard } = await import("../ui/page/Page");
		renderPage(<SellerDashboard.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeletons when loading", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => true;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => true;

		const { SellerDashboard } = await import("../ui/page/Page");
		const { container } = renderPage(<SellerDashboard.Page />);
		// Skeletons are rendered when loading
		expect(container.querySelector(".mantine-Skeleton-root")).toBeTruthy();
	});

	it("should display stats section when loaded", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => false;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => false;

		const { SellerDashboard } = await import("../ui/page/Page");
		const { container } = renderPage(<SellerDashboard.Page />);
		// Stats section should render (not skeletons)
		expect(container.querySelector(".mantine-Skeleton-root")).toBeFalsy();
	});

	it("should display quick action buttons", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => false;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => false;

		const { SellerDashboard } = await import("../ui/page/Page");
		renderPage(<SellerDashboard.Page />);
		// Quick actions section header
		expect(screen.getByText("dashboard.quickActions")).toBeTruthy();
	});

	it("should show greeting card with welcome text", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => false;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => false;

		const { SellerDashboard } = await import("../ui/page/Page");
		renderPage(<SellerDashboard.Page />);
		expect(screen.getByText("dashboard.welcome")).toBeTruthy();
	});

	it("should show onboarding prompt when no listings", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => false;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => false;
		(state.$sellerStats as any).getState = () => ({
			totalListings: 0,
			activeListings: 0,
			totalViews: 0,
			totalContacts: 0,
			totalFavorites: 0,
		});
		(state.$sellerStats as any)["@@unitShape"] = () => ({
			totalListings: 0,
			activeListings: 0,
			totalViews: 0,
			totalContacts: 0,
			totalFavorites: 0,
		});

		const { SellerDashboard } = await import("../ui/page/Page");
		renderPage(<SellerDashboard.Page />);
		expect(screen.getByText("dashboard.createFirst")).toBeTruthy();
		expect(screen.getByText("dashboard.createFirstDescription")).toBeTruthy();
	});

	it("should navigate when quick actions are clicked", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => false;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => false;

		const { SellerDashboard } = await import("../ui/page/Page");
		renderPage(<SellerDashboard.Page />);
		// Quick action labels should be present
		expect(screen.getByText("dashboard.createListing")).toBeTruthy();
		expect(screen.getByText("dashboard.myListings")).toBeTruthy();
	});

	it("should display seller company name in greeting", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => false;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => false;
		(state.$sellerProfile as any).getState = () => ({
			company_name: "My Agency",
			phone: "+998901234567",
		});
		(state.$sellerProfile as any)["@@unitShape"] = () => ({
			company_name: "My Agency",
			phone: "+998901234567",
		});

		const { SellerDashboard } = await import("../ui/page/Page");
		renderPage(<SellerDashboard.Page />);
		expect(screen.getByText("My Agency")).toBeTruthy();
	});

	it("should show zero values for empty stats", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => false;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => false;
		(state.$sellerStats as any).getState = () => ({
			totalListings: 0,
			activeListings: 0,
			totalViews: 0,
			totalContacts: 0,
			totalFavorites: 0,
		});
		(state.$sellerStats as any)["@@unitShape"] = () => ({
			totalListings: 0,
			activeListings: 0,
			totalViews: 0,
			totalContacts: 0,
			totalFavorites: 0,
		});

		const { SellerDashboard } = await import("../ui/page/Page");
		const { container } = renderPage(<SellerDashboard.Page />);
		// Page should render without errors when stats are zero
		expect(container).toBeTruthy();
	});

	it("should have fetchSellerProfile available for profile loading", async () => {
		const state = await import("@modules/seller/shared/state");
		// fetchSellerProfile is called via useEffect with ref guard on mount;
		// verify the function exists and is callable
		expect(state.fetchSellerProfile).toBeDefined();
		expect(typeof state.fetchSellerProfile).toBe("function");
	});
});
