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
	$selectedListing: {
		getState: () => ({
			id: "listing-1",
			title: "Test Listing",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "pending",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: null,
			phone: null,
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		}),
		"@@unitShape": () => ({
			id: "listing-1",
			title: "Test Listing",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "pending",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: null,
			phone: null,
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		}),
	},
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

// Mock react-router-dom params
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useParams: () => ({ id: "listing-1" }),
	};
});

// Mock react-i18next
vi.mock("react-i18next", () => ({
	useTranslation: () => ({
		t: (key: string) => {
			const map: Record<string, string> = {
				"listingDetail.backToListings": "Back to Listings",
				"listingDetail.sellerContact": "Seller & Contact",
				"listingDetail.sourceInfo": "Source Info",
				"listingDetail.sourceType": "Source Type",
				"listingDetail.sourceUrl": "Source URL",
				"listingDetail.moderationHistory": "Moderation History",
				"listingDetail.moderatedAt": "Moderated At",
				"listingDetail.approveListing": "Approve Listing",
				"listingDetail.rejectListing": "Reject Listing",
				"listingDetail.approveListingDesc":
					"Are you sure you want to approve this listing?",
				"listingDetail.rejectListingDesc":
					"Are you sure you want to reject this listing?",
				"common.type": "Type",
				"common.rooms": "Rooms",
				"common.area": "Area",
				"common.floor": "Floor",
				"common.location": "Location",
				"common.district": "District",
				"common.address": "Address",
				"common.description": "Description",
				"common.seller": "Seller",
				"common.phone": "Phone",
				"common.na": "N/A",
				"common.created": "Created",
				"common.notes": "Notes",
				"common.notesOptional": "Notes (optional)",
				"common.addNotes": "Add notes...",
				"common.reject": "Reject",
				"common.approve": "Approve",
				"common.cancel": "Cancel",
				"common.rejectionReason": "Rejection Reason",
				"common.enterReason": "Enter reason...",
				"common.noImages": "No images",
				"common.tapToZoom": "Tap to zoom",
			};
			return map[key] || key;
		},
		i18n: { language: "en" },
	}),
}));

// Mock shared dependencies
vi.mock("@shared/lib/date", () => ({
	formatDate: (d: string) => new Date(d).toLocaleDateString(),
	formatDateTime: (d: string) => new Date(d).toLocaleString(),
}));

vi.mock("@app/styles/theme", () => ({
	formatPrice: (price: number, _currency: string) => `$${price}`,
}));

vi.mock("@shared/lib/regions", () => ({
	translateDistrict: (key: string) => key,
}));

// Mock CSS
vi.mock("@modules/admin/shared/ui/admin.css", () => ({}));

describe("AdminListingDetailPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeleton when isLoading is true", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$isLoadingListingDetail as any).getState = () => true;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => true;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(document.querySelector(".admin-skeleton")).toBeTruthy();
	});

	it("should display listing info when loaded", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListing = {
			id: "listing-1",
			title: "Beautiful Apartment",
			price: 75000,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "pending",
			source_type: "manual",
			images: [],
			district: "yunusabad",
			address: "123 Main St",
			rooms: 3,
			area: 80,
			floor: 5,
			total_floors: 9,
			description: "A nice place",
			seller_name: "John Doe",
			phone: "+998901234567",
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		};
		(state.$selectedListing as any).getState = () => mockListing;
		(state.$selectedListing as any)["@@unitShape"] = () => mockListing;
		(state.$isLoadingListingDetail as any).getState = () => false;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(screen.getByText("Beautiful Apartment")).toBeTruthy();
		expect(screen.getByText("$75000")).toBeTruthy();
	});

	it("should display no images placeholder when no images", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListing = {
			id: "listing-1",
			title: "Test",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "pending",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: null,
			phone: null,
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		};
		(state.$selectedListing as any).getState = () => mockListing;
		(state.$selectedListing as any)["@@unitShape"] = () => mockListing;
		(state.$isLoadingListingDetail as any).getState = () => false;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(screen.getByText("No images")).toBeTruthy();
	});

	it("should display approve and reject buttons for pending listing", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListing = {
			id: "listing-1",
			title: "Test",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "pending",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: null,
			phone: null,
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		};
		(state.$selectedListing as any).getState = () => mockListing;
		(state.$selectedListing as any)["@@unitShape"] = () => mockListing;
		(state.$isLoadingListingDetail as any).getState = () => false;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(screen.getByText("Approve")).toBeTruthy();
		expect(screen.getByText("Reject")).toBeTruthy();
	});

	it("should not display action buttons for approved listing", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListing = {
			id: "listing-1",
			title: "Test",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "approved",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: null,
			phone: null,
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		};
		(state.$selectedListing as any).getState = () => mockListing;
		(state.$selectedListing as any)["@@unitShape"] = () => mockListing;
		(state.$isLoadingListingDetail as any).getState = () => false;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(screen.queryByText("Approve")).toBeNull();
	});

	it("should display moderation status badge", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListing = {
			id: "listing-1",
			title: "Test",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "approved",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: null,
			phone: null,
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		};
		(state.$selectedListing as any).getState = () => mockListing;
		(state.$selectedListing as any)["@@unitShape"] = () => mockListing;
		(state.$isLoadingListingDetail as any).getState = () => false;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(screen.getByText("approved")).toBeTruthy();
	});

	it("should display seller contact section", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListing = {
			id: "listing-1",
			title: "Test",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "pending",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: "Test Seller",
			phone: "+998901111111",
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		};
		(state.$selectedListing as any).getState = () => mockListing;
		(state.$selectedListing as any)["@@unitShape"] = () => mockListing;
		(state.$isLoadingListingDetail as any).getState = () => false;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(screen.getByText("Seller & Contact")).toBeTruthy();
		expect(screen.getByText("Test Seller")).toBeTruthy();
	});

	it("should display source info section", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListing = {
			id: "listing-1",
			title: "Test",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "pending",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: null,
			phone: null,
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		};
		(state.$selectedListing as any).getState = () => mockListing;
		(state.$selectedListing as any)["@@unitShape"] = () => mockListing;
		(state.$isLoadingListingDetail as any).getState = () => false;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(screen.getByText("Source Info")).toBeTruthy();
	});

	it("should display back to listings button", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockListing = {
			id: "listing-1",
			title: "Test",
			price: 100,
			currency: "USD",
			property_type: "apartment",
			type: "sell",
			moderation_status: "pending",
			source_type: "manual",
			images: [],
			district: "",
			address: "",
			rooms: null,
			area: null,
			floor: null,
			total_floors: null,
			description: null,
			seller_name: null,
			phone: null,
			seller_phone: null,
			source_url: null,
			moderation_notes: null,
			moderated_at: null,
			created_at: "2024-01-01T00:00:00Z",
		};
		(state.$selectedListing as any).getState = () => mockListing;
		(state.$selectedListing as any)["@@unitShape"] = () => mockListing;
		(state.$isLoadingListingDetail as any).getState = () => false;
		(state.$isLoadingListingDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminListingDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminListingDetailPage />);
		expect(screen.getByText("Back to Listings")).toBeTruthy();
	});
});
