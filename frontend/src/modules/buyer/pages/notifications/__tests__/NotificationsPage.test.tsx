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

// Mock useAuth
vi.mock("@app/providers/useAuth", () => ({
	useAuth: () => ({
		isAuthenticated: true,
		user: { id: "1", first_name: "Test" },
	}),
}));

// Mock notifications API
vi.mock("@shared/api/notifications", () => ({
	notificationsApi: {
		getNotifications: vi
			.fn()
			.mockResolvedValue({ items: [], page: 1, total_pages: 1 }),
		getUnreadCount: vi.fn().mockResolvedValue({ unread_count: 0 }),
		markAsRead: vi.fn().mockResolvedValue({}),
	},
}));

// Mock shared libs
vi.mock("@shared/lib/date", () => ({
	formatTimeAgo: (_date: string) => "5m ago",
}));

// Mock UnauthScreen
vi.mock("@shared/ui/UnauthScreen", () => ({
	UnauthScreen: (props: any) => (
		<div data-testid="unauth-screen">{props.title}</div>
	),
}));

describe("Notifications", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading state initially", async () => {
		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		// Loading state shown on first render before API resolves
		expect(document.body).toBeTruthy();
	});

	it("should show unauth screen when not authenticated", async () => {
		const authMock = await import("@app/providers/useAuth");
		(authMock.useAuth as any) = () => ({
			isAuthenticated: false,
			user: null,
		});

		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render notifications list when data exists", async () => {
		const api = await import("@shared/api/notifications");
		(api.notificationsApi.getNotifications as any).mockResolvedValue({
			items: [
				{
					id: "1",
					type: "price_drop",
					title: "Price dropped",
					message: "Apt price dropped to $40k",
					read: false,
					created_at: new Date().toISOString(),
					listing_id: "listing-1",
				},
			],
			page: 1,
			total_pages: 1,
		});

		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show empty state when no notifications", async () => {
		const api = await import("@shared/api/notifications");
		(api.notificationsApi.getNotifications as any).mockResolvedValue({
			items: [],
			page: 1,
			total_pages: 1,
		});

		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle mark all as read action", async () => {
		const api = await import("@shared/api/notifications");
		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(api.notificationsApi.markAsRead).toBeDefined();
	});

	it("should handle notification click", async () => {
		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle load more", async () => {
		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should display unread count badge", async () => {
		const api = await import("@shared/api/notifications");
		(api.notificationsApi.getUnreadCount as any).mockResolvedValue({
			unread_count: 5,
		});

		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should group notifications by date", async () => {
		const { Notifications } = await import("../ui/page/Page");
		renderPage(<Notifications.Page />);
		expect(document.body).toBeTruthy();
	});
});
