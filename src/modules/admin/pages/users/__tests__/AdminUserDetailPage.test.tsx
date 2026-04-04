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
	$selectedUser: {
		getState: () => ({
			id: "user-1",
			first_name: "Test",
			last_name: "",
			username: "",
			phone: "",
			role: "user",
			approval_status: "pending",
			telegram_id: "1",
			language: "en",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: false,
		}),
		"@@unitShape": () => ({
			id: "user-1",
			first_name: "Test",
			last_name: "",
			username: "",
			phone: "",
			role: "user",
			approval_status: "pending",
			telegram_id: "1",
			language: "en",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: false,
		}),
	},
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

// Mock react-router-dom params
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useParams: () => ({ id: "user-1" }),
	};
});

// Mock react-i18next
vi.mock("react-i18next", () => ({
	useTranslation: () => ({
		t: (key: string) => {
			const map: Record<string, string> = {
				"userDetail.backToUsers": "Back to Users",
				"userDetail.contactInfo": "Contact Info",
				"userDetail.telegramId": "Telegram ID",
				"userDetail.language": "Language",
				"userDetail.russian": "Russian",
				"userDetail.uzbek": "Uzbek",
				"userDetail.accountStatus": "Account Status",
				"userDetail.registered": "Registered",
				"userDetail.onboarding": "Onboarding",
				"userDetail.completed": "Completed",
				"userDetail.notCompleted": "Not Completed",
				"userDetail.reviewHistory": "Review History",
				"userDetail.reviewedAt": "Reviewed At",
				"userDetail.approveUser": "Approve User",
				"userDetail.rejectUser": "Reject User",
				"userDetail.approveUserDesc":
					"Are you sure you want to approve this user?",
				"userDetail.rejectUserDesc":
					"Are you sure you want to reject this user?",
				"common.phone": "Phone",
				"common.notProvided": "Not provided",
				"common.notes": "Notes",
				"common.notesOptional": "Notes (optional)",
				"common.addNotes": "Add notes...",
				"common.reject": "Reject",
				"common.approve": "Approve",
				"common.cancel": "Cancel",
				"common.rejectionReason": "Rejection Reason",
				"common.enterReason": "Enter reason...",
			};
			return map[key] || key;
		},
		i18n: { language: "en" },
	}),
}));

// Mock shared lib/date
vi.mock("@shared/lib/date", () => ({
	formatDate: (d: string) => new Date(d).toLocaleDateString(),
	formatDateTime: (d: string) => new Date(d).toLocaleString(),
}));

// Mock CSS
vi.mock("@modules/admin/shared/ui/admin.css", () => ({}));

describe("AdminUserDetailPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeleton when isLoading is true", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$isLoadingUserDetail as any).getState = () => true;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => true;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(document.querySelector(".admin-skeleton")).toBeTruthy();
	});

	it("should display user info when user is loaded", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUser = {
			id: "user-1",
			first_name: "John",
			last_name: "Doe",
			username: "johndoe",
			phone: "+998901234567",
			role: "seller",
			approval_status: "pending",
			telegram_id: "123456",
			language: "ru",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: true,
		};
		(state.$selectedUser as any).getState = () => mockUser;
		(state.$selectedUser as any)["@@unitShape"] = () => mockUser;
		(state.$isLoadingUserDetail as any).getState = () => false;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(screen.getByText("John Doe")).toBeTruthy();
		expect(screen.getByText("@johndoe")).toBeTruthy();
	});

	it("should display approve and reject buttons for pending user", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUser = {
			id: "user-1",
			first_name: "John",
			last_name: "Doe",
			username: "johndoe",
			phone: "+998901234567",
			role: "seller",
			approval_status: "pending",
			telegram_id: "123456",
			language: "ru",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: false,
		};
		(state.$selectedUser as any).getState = () => mockUser;
		(state.$selectedUser as any)["@@unitShape"] = () => mockUser;
		(state.$isLoadingUserDetail as any).getState = () => false;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(screen.getByText("Approve")).toBeTruthy();
		expect(screen.getByText("Reject")).toBeTruthy();
	});

	it("should not display action buttons for non-pending user", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUser = {
			id: "user-1",
			first_name: "John",
			last_name: "Doe",
			username: "johndoe",
			phone: "+998901234567",
			role: "seller",
			approval_status: "approved",
			telegram_id: "123456",
			language: "ru",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: true,
		};
		(state.$selectedUser as any).getState = () => mockUser;
		(state.$selectedUser as any)["@@unitShape"] = () => mockUser;
		(state.$isLoadingUserDetail as any).getState = () => false;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(screen.queryByText("Approve")).toBeNull();
	});

	it("should display approval status badge", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUser = {
			id: "user-1",
			first_name: "John",
			last_name: "Doe",
			username: "",
			phone: "",
			role: "user",
			approval_status: "approved",
			telegram_id: "123",
			language: "en",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: true,
		};
		(state.$selectedUser as any).getState = () => mockUser;
		(state.$selectedUser as any)["@@unitShape"] = () => mockUser;
		(state.$isLoadingUserDetail as any).getState = () => false;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(screen.getByText("approved")).toBeTruthy();
	});

	it("should display back to users button", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUser = {
			id: "user-1",
			first_name: "Test",
			last_name: "",
			username: "",
			phone: "",
			role: "user",
			approval_status: "pending",
			telegram_id: "1",
			language: "en",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: false,
		};
		(state.$selectedUser as any).getState = () => mockUser;
		(state.$selectedUser as any)["@@unitShape"] = () => mockUser;
		(state.$isLoadingUserDetail as any).getState = () => false;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(screen.getByText("Back to Users")).toBeTruthy();
	});

	it("should display contact info section", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUser = {
			id: "user-1",
			first_name: "Test",
			last_name: "",
			username: "",
			phone: "+998901234567",
			role: "user",
			approval_status: "pending",
			telegram_id: "1",
			language: "ru",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: false,
		};
		(state.$selectedUser as any).getState = () => mockUser;
		(state.$selectedUser as any)["@@unitShape"] = () => mockUser;
		(state.$isLoadingUserDetail as any).getState = () => false;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(screen.getByText("Contact Info")).toBeTruthy();
		expect(screen.getByText("+998901234567")).toBeTruthy();
	});

	it("should display account status section", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUser = {
			id: "user-1",
			first_name: "Test",
			last_name: "",
			username: "",
			phone: "",
			role: "user",
			approval_status: "pending",
			telegram_id: "1",
			language: "en",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: true,
		};
		(state.$selectedUser as any).getState = () => mockUser;
		(state.$selectedUser as any)["@@unitShape"] = () => mockUser;
		(state.$isLoadingUserDetail as any).getState = () => false;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(screen.getByText("Account Status")).toBeTruthy();
		expect(screen.getByText("Completed")).toBeTruthy();
	});

	it("should display review history when notes exist", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUser = {
			id: "user-1",
			first_name: "Test",
			last_name: "",
			username: "",
			phone: "",
			role: "user",
			approval_status: "approved",
			telegram_id: "1",
			language: "en",
			created_at: "2024-01-01T00:00:00Z",
			onboarding_completed: true,
			approval_notes: "All good, approved.",
			approved_at: "2024-02-01T00:00:00Z",
		};
		(state.$selectedUser as any).getState = () => mockUser;
		(state.$selectedUser as any)["@@unitShape"] = () => mockUser;
		(state.$isLoadingUserDetail as any).getState = () => false;
		(state.$isLoadingUserDetail as any)["@@unitShape"] = () => false;

		const { Main: AdminUserDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminUserDetailPage />);
		expect(screen.getByText("Review History")).toBeTruthy();
		expect(screen.getByText("All good, approved.")).toBeTruthy();
	});
});
