import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen, fireEvent } from "@/test/helpers";

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
				"users.title": "Users",
				"users.subtitle": "Manage user accounts",
				"users.searchPlaceholder": "Search users...",
				"users.noUsersFound": "No users found",
				"users.user": "User",
				"users.seller": "Seller",
				"users.admin": "Admin",
				"common.all": "All",
				"common.pending": "Pending",
				"common.approved": "Approved",
				"common.rejected": "Rejected",
				"common.allRoles": "All Roles",
				"common.tryAdjustingFilters": "Try adjusting your filters",
			};
			if (key === "users.showing" && opts)
				return `Showing ${opts.count} of ${opts.total}`;
			return map[key] || key;
		},
		i18n: { language: "en" },
	}),
}));

// Mock mantine hooks
vi.mock("@mantine/hooks", () => ({
	useDebouncedValue: (value: any) => [value],
}));

// Mock CSS
vi.mock("@modules/admin/shared/ui/admin.css", () => ({}));

describe("AdminUsers", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeleton when isLoading is true", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$isLoadingUsers as any).getState = () => true;
		(state.$isLoadingUsers as any)["@@unitShape"] = () => true;

		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(document.querySelector(".admin-skeleton-card")).toBeTruthy();
	});

	it("should display user list when users exist", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUsers = [
			{
				id: "1",
				first_name: "John",
				last_name: "Doe",
				username: "johndoe",
				phone: "+998901234567",
				role: "seller",
				approval_status: "approved",
				telegram_id: "123",
				created_at: "2024-01-01T00:00:00Z",
			},
			{
				id: "2",
				first_name: "Jane",
				last_name: "Smith",
				username: "janesmith",
				phone: "+998907654321",
				role: "user",
				approval_status: "pending",
				telegram_id: "456",
				created_at: "2024-01-02T00:00:00Z",
			},
		];
		(state.$users as any).getState = () => mockUsers;
		(state.$users as any)["@@unitShape"] = () => mockUsers;
		(state.$isLoadingUsers as any).getState = () => false;
		(state.$isLoadingUsers as any)["@@unitShape"] = () => false;
		const pag = { total: 2, page: 1, per_page: 20, totalPages: 1 };
		(state.$usersPagination as any).getState = () => pag;
		(state.$usersPagination as any)["@@unitShape"] = () => pag;

		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(screen.getByText("John Doe")).toBeTruthy();
		expect(screen.getByText("Jane Smith")).toBeTruthy();
	});

	it("should render approval status chip filters", async () => {
		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(screen.getByText("All")).toBeTruthy();
		expect(screen.getByText("Pending")).toBeTruthy();
		expect(screen.getByText("Approved")).toBeTruthy();
		expect(screen.getByText("Rejected")).toBeTruthy();
	});

	it("should render role chip filters", async () => {
		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(screen.getByText("All Roles")).toBeTruthy();
		expect(screen.getByText("User")).toBeTruthy();
		expect(screen.getByText("Seller")).toBeTruthy();
		expect(screen.getByText("Admin")).toBeTruthy();
	});

	it("should display search input", async () => {
		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(screen.getByPlaceholderText("Search users...")).toBeTruthy();
	});

	it("should display page title", async () => {
		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(screen.getByText("Users")).toBeTruthy();
		expect(screen.getByText("Manage user accounts")).toBeTruthy();
	});

	it("should show empty state when no users", async () => {
		const state = await import("@modules/admin/shared/state");
		(state.$users as any).getState = () => [];
		(state.$users as any)["@@unitShape"] = () => [];
		(state.$isLoadingUsers as any).getState = () => false;
		(state.$isLoadingUsers as any)["@@unitShape"] = () => false;

		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(screen.getByText("No users found")).toBeTruthy();
	});

	it("should display user approval status badges", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUsers = [
			{
				id: "1",
				first_name: "Alice",
				last_name: "",
				username: "",
				phone: "",
				role: "user",
				approval_status: "pending",
				telegram_id: "111",
				created_at: "2024-01-01T00:00:00Z",
			},
		];
		(state.$users as any).getState = () => mockUsers;
		(state.$users as any)["@@unitShape"] = () => mockUsers;
		(state.$isLoadingUsers as any).getState = () => false;
		(state.$isLoadingUsers as any)["@@unitShape"] = () => false;
		const pag = { total: 1, page: 1, per_page: 20, totalPages: 1 };
		(state.$usersPagination as any).getState = () => pag;
		(state.$usersPagination as any)["@@unitShape"] = () => pag;

		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(screen.getByText("pending")).toBeTruthy();
	});

	it("should display user role pills", async () => {
		const state = await import("@modules/admin/shared/state");
		const mockUsers = [
			{
				id: "1",
				first_name: "Bob",
				last_name: "",
				username: "",
				phone: "",
				role: "seller",
				approval_status: "approved",
				telegram_id: "222",
				created_at: "2024-01-01T00:00:00Z",
			},
		];
		(state.$users as any).getState = () => mockUsers;
		(state.$users as any)["@@unitShape"] = () => mockUsers;
		(state.$isLoadingUsers as any).getState = () => false;
		(state.$isLoadingUsers as any)["@@unitShape"] = () => false;
		const pag = { total: 1, page: 1, per_page: 20, totalPages: 1 };
		(state.$usersPagination as any).getState = () => pag;
		(state.$usersPagination as any)["@@unitShape"] = () => pag;

		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		expect(screen.getByText("seller")).toBeTruthy();
	});

	it("should handle search input change", async () => {
		const { AdminUsers } = await import("../ui/page/Page");
		renderPage(<AdminUsers.Page />);
		const searchInput = screen.getByPlaceholderText("Search users...");
		fireEvent.change(searchInput, { target: { value: "test" } });
		expect((searchInput as HTMLInputElement).value).toBe("test");
	});
});
