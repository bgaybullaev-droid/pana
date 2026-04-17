import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

const mockListings = [
	{
		id: "1",
		title: "Test Apartment",
		price: 50000,
		currency: "USD",
		property_type: "apartment",
		rooms: 3,
		area: 80,
		district: "chilanzar",
		status: "active",
		views_count: 42,
		contacts_count: 5,
		primary_image_url: null,
		source_type: "MANUAL",
	},
	{
		id: "2",
		title: "Paused House",
		price: 120000,
		currency: "USD",
		property_type: "house",
		rooms: 5,
		area: 200,
		district: "yunusabad",
		status: "paused",
		views_count: 10,
		contacts_count: 0,
		primary_image_url: null,
		source_type: null,
	},
];

// Mock seller shared state
vi.mock("@modules/seller/shared/state", () => ({
	$sellerListings: {
		getState: () => mockListings,
		"@@unitShape": () => mockListings,
	},
	$isLoadingListings: { getState: () => false, "@@unitShape": () => false },
	fetchSellerListings: vi.fn(),
	pauseListing: vi.fn(),
	activateListing: vi.fn(),
	deleteListing: vi.fn(),
	pauseListingFx: { doneData: { watch: vi.fn(() => vi.fn()) } },
	activateListingFx: { doneData: { watch: vi.fn(() => vi.fn()) } },
	deleteListingFx: { doneData: { watch: vi.fn(() => vi.fn()) } },
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

// Mock shared API
vi.mock("@shared/api/sellerCrawledListings", () => ({
	fetchSellerOLXListings: vi.fn().mockResolvedValue({ items: [], total: 0 }),
	fetchSellerTelegramListings: vi
		.fn()
		.mockResolvedValue({ items: [], total: 0 }),
	claimOlxListing: vi.fn(),
}));

// Mock shared UI components
vi.mock("@shared/ui/EmptyState", () => ({
	EmptyState: ({ title, description }: any) => (
		<div data-testid="empty-state">
			<span>{title}</span>
			<span>{description}</span>
		</div>
	),
}));

vi.mock("@shared/ui/PillTabs", () => ({
	PillTabs: ({ tabs, onChange }: any) => (
		<div data-testid="pill-tabs">
			{tabs.map((tab: any) => (
				<button
					key={tab.value}
					data-testid={`tab-${tab.value}`}
					onClick={() => onChange(tab.value)}
				>
					{tab.label} ({tab.count})
				</button>
			))}
		</div>
	),
}));

vi.mock("@shared/ui/ListingImageThumbnail", () => ({
	ListingImageThumbnail: () => <div data-testid="listing-thumbnail" />,
}));

vi.mock("@app/styles/theme", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@app/styles/theme")>();
	return {
		...actual,
		formatPrice: (price: number, currency: string) => `${price} ${currency}`,
	};
});

vi.mock("@shared/lib/regions", () => ({
	translateDistrict: (key: string) => key,
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
			pathname: "/my-listings",
			search: "",
			hash: "",
			state: null,
		}),
	};
});

describe("SellerListings", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeletons when loading", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$sellerListings as any).getState = () => [];
		(state.$sellerListings as any)["@@unitShape"] = () => [];
		(state.$isLoadingListings as any).getState = () => true;
		(state.$isLoadingListings as any)["@@unitShape"] = () => true;

		const { SellerListings } = await import("../ui/page/Page");
		const { container } = renderPage(<SellerListings.Page />);
		expect(container.querySelector(".mantine-Skeleton-root")).toBeTruthy();
	});

	it.skip("should display listing cards with price and info", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$sellerListings as any).getState = () => mockListings;
		(state.$sellerListings as any)["@@unitShape"] = () => mockListings;
		(state.$isLoadingListings as any).getState = () => false;
		(state.$isLoadingListings as any)["@@unitShape"] = () => false;

		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		expect(screen.getByText("50000 USD")).toBeTruthy();
		expect(screen.getByText("120000 USD")).toBeTruthy();
	});

	it.skip("should render filter tabs", async () => {
		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		expect(screen.getByTestId("pill-tabs")).toBeTruthy();
		expect(screen.getByTestId("tab-all")).toBeTruthy();
		expect(screen.getByTestId("tab-platform")).toBeTruthy();
	});

	it("should show empty state when no listings", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$sellerListings as any).getState = () => [];
		(state.$sellerListings as any)["@@unitShape"] = () => [];
		(state.$isLoadingListings as any).getState = () => false;
		(state.$isLoadingListings as any)["@@unitShape"] = () => false;

		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		expect(screen.getByTestId("empty-state")).toBeTruthy();
	});

	it("should display page header with title", async () => {
		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		expect(screen.getByText("listings.myListings")).toBeTruthy();
	});

	it.skip("should display add button", async () => {
		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		expect(screen.getByText("listings.add")).toBeTruthy();
	});

	it.skip("should display source badges on listing cards", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$sellerListings as any).getState = () => mockListings;
		(state.$sellerListings as any)["@@unitShape"] = () => mockListings;
		(state.$isLoadingListings as any).getState = () => false;
		(state.$isLoadingListings as any)["@@unitShape"] = () => false;

		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		// Platform source badges
		const badges = screen.getAllByText("listings.platform");
		expect(badges.length).toBeGreaterThan(0);
	});

	it("should call fetchSellerListings on mount", async () => {
		const state = await import("@modules/seller/shared/state");

		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		expect(state.fetchSellerListings).toHaveBeenCalledWith({});
	});

	it.skip("should display status labels for listing cards", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$sellerListings as any).getState = () => mockListings;
		(state.$sellerListings as any)["@@unitShape"] = () => mockListings;
		(state.$isLoadingListings as any).getState = () => false;
		(state.$isLoadingListings as any)["@@unitShape"] = () => false;

		const { SellerListings } = await import("../ui/page/Page");
		renderPage(<SellerListings.Page />);
		expect(screen.getByText("listings.statusActive")).toBeTruthy();
		expect(screen.getByText("listings.statusPaused")).toBeTruthy();
	});
});
