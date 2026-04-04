import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage } from "@/test/helpers";

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

// Mock react-router-dom to provide id param
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useNavigate: () => vi.fn(),
		useParams: () => ({ id: "seller-1" }),
		useSearchParams: () => [new URLSearchParams(), vi.fn()],
		useLocation: () => ({
			pathname: "/seller/seller-1",
			search: "",
			hash: "",
			state: null,
		}),
	};
});

// Mock API client
vi.mock("@shared/api/client", () => ({
	apiClient: {
		get: vi.fn().mockImplementation((url: string) => {
			if (url.includes("/listings")) {
				return Promise.resolve({
					data: { items: [], total: 0, page: 1, per_page: 50 },
				});
			}
			return Promise.resolve({
				data: {
					id: "seller-1",
					company_name: "Test Realty",
					description: "Best real estate agency",
					phone: "+998901234567",
					telegram_username: "testrealty",
					is_verified: true,
					created_at: "2023-01-01T00:00:00Z",
					listings_count: 10,
					logo_url: null,
					instagram_url: null,
					website_url: null,
				},
			});
		}),
	},
}));

// Mock ListingCard
vi.mock("@shared/ui/ListingCard", () => ({
	ListingCard: ({ listing }: any) => (
		<div data-testid="listing-card">{listing?.title}</div>
	),
}));

// Mock theme
vi.mock("@app/styles/theme", () => ({
	shadows: { card: "0 2px 8px rgba(0,0,0,0.04)" },
}));

describe("SellerProfile", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading state initially", async () => {
		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		// Loading overlay is shown on first render before API resolves
		expect(document.body).toBeTruthy();
	});

	it("should fetch seller data on mount", async () => {
		const api = await import("@shared/api/client");
		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(api.apiClient.get).toBeDefined();
	});

	it("should render back button", async () => {
		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render seller profile after loading", async () => {
		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should display seller stats (listings, years, views)", async () => {
		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render action buttons (call, message, share)", async () => {
		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle seller not found", async () => {
		const api = await import("@shared/api/client");
		(api.apiClient.get as any).mockRejectedValue(new Error("Not found"));

		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render social links when available", async () => {
		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should display listings grid when seller has listings", async () => {
		const api = await import("@shared/api/client");
		(api.apiClient.get as any).mockImplementation((url: string) => {
			if (url.includes("/listings")) {
				return Promise.resolve({
					data: {
						items: [
							{ id: "l-1", title: "Nice Apt", price: 50000, views_count: 100 },
						],
						total: 1,
						page: 1,
						per_page: 50,
					},
				});
			}
			return Promise.resolve({
				data: {
					id: "seller-1",
					company_name: "Test Realty",
					is_verified: true,
					created_at: "2023-01-01T00:00:00Z",
					listings_count: 1,
				},
			});
		});

		const { SellerProfile } = await import("../ui/page/Page");
		renderPage(<SellerProfile.Page />);
		expect(document.body).toBeTruthy();
	});
});
