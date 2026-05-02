import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen, fireEvent } from "@/test/helpers";

const mockProfile = {
	company_name: "Premium Realty",
	phone: "+998901234567",
	email: "info@premiumrealty.uz",
	description: "Leading real estate agency in Tashkent",
	phone_public: true,
	is_verified: true,
	telegram_username: "@premiumrealty",
	instagram_url: "https://instagram.com/premiumrealty",
	website_url: "https://premiumrealty.uz",
	logo_url: null,
	listings_count: 15,
	total_views: 2400,
	total_contacts: 38,
	created_at: "2024-06-15T10:00:00Z",
};

// Mock seller shared state
vi.mock("@modules/seller/shared/state", () => ({
	$sellerProfile: {
		getState: () => mockProfile,
		"@@unitShape": () => mockProfile,
	},
	$isLoadingProfile: { getState: () => false, "@@unitShape": () => false },
	updateSellerProfile: vi.fn(),
	updateSellerProfileFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
		doneData: { watch: vi.fn(() => vi.fn()) },
		failData: { watch: vi.fn(() => vi.fn()) },
		done: { watch: vi.fn(() => vi.fn()) },
		fail: { watch: vi.fn(() => vi.fn()) },
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

// Mock useEffectorNotification
vi.mock("@shared/hooks/useEffectorNotification", () => ({
	useEffectorNotification: vi.fn(),
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

vi.mock("@shared/ui/FormSection", () => ({
	FormSection: ({ title, children }: any) => (
		<div data-testid="form-section">
			<span data-testid="form-section-title">{title}</span>
			{children}
		</div>
	),
}));

vi.mock("@shared/lib/date", () => ({
	formatMonthYear: (_date: string) => "June 2024",
}));

describe("SellerProfileEdit", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { SellerProfileEdit } = await import("../ui/page/Page");
		renderPage(<SellerProfileEdit.Page />);
		expect(document.body).toBeTruthy();
	});

	it.skip("should display seller profile info", async () => {
		const { SellerProfileEdit } = await import("../ui/page/Page");
		renderPage(<SellerProfileEdit.Page />);
		expect(screen.getByText("Premium Realty")).toBeTruthy();
		// Phone appears in hero card and contact row
		const phoneElements = screen.getAllByText("+998901234567");
		expect(phoneElements.length).toBeGreaterThanOrEqual(1);
	});

	it("should display edit button in view mode", async () => {
		const { SellerProfileEdit } = await import("../ui/page/Page");
		renderPage(<SellerProfileEdit.Page />);
		expect(screen.getByText("profile.edit")).toBeTruthy();
	});

	it("should switch to edit mode when edit button clicked", async () => {
		const { SellerProfileEdit } = await import("../ui/page/Page");
		renderPage(<SellerProfileEdit.Page />);
		const editButton = screen.getByText("profile.edit");
		fireEvent.click(editButton);
		// In edit mode, company name input and save/cancel buttons appear
		expect(screen.getByText("profile.companyName")).toBeTruthy();
		expect(screen.getByText("profile.save")).toBeTruthy();
		expect(screen.getByText("profile.cancel")).toBeTruthy();
	});

	it("should display stat cards with profile data", async () => {
		const { SellerProfileEdit } = await import("../ui/page/Page");
		renderPage(<SellerProfileEdit.Page />);
		const statCards = screen.getAllByTestId("stat-card");
		expect(statCards.length).toBe(3);
	});

	it.skip("should display contact rows with phone and email", async () => {
		const { SellerProfileEdit } = await import("../ui/page/Page");
		renderPage(<SellerProfileEdit.Page />);
		// Phone appears in both hero section and contacts section
		const phoneElements = screen.getAllByText("+998901234567");
		expect(phoneElements.length).toBeGreaterThanOrEqual(2);
		expect(screen.getByText("info@premiumrealty.uz")).toBeTruthy();
	});

	it("should show save and cancel buttons in edit mode", async () => {
		const { SellerProfileEdit } = await import("../ui/page/Page");
		renderPage(<SellerProfileEdit.Page />);
		fireEvent.click(screen.getByText("profile.edit"));
		expect(screen.getByText("profile.save")).toBeTruthy();
		expect(screen.getByText("profile.cancel")).toBeTruthy();
	});

	it("should return to view mode when cancel clicked", async () => {
		const { SellerProfileEdit } = await import("../ui/page/Page");
		renderPage(<SellerProfileEdit.Page />);
		fireEvent.click(screen.getByText("profile.edit"));
		expect(screen.getByText("profile.cancel")).toBeTruthy();
		fireEvent.click(screen.getByText("profile.cancel"));
		// Back in view mode - edit button should reappear
		expect(screen.getByText("profile.edit")).toBeTruthy();
	});
});
