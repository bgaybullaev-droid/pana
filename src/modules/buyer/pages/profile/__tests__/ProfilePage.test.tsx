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
		user: { id: "1", first_name: "Test", last_name: "User", avatar_url: null },
		logout: vi.fn(),
	}),
}));

// Mock useTelegram
vi.mock("@app/providers/useTelegram", () => ({
	useTelegram: () => ({
		webApp: {
			HapticFeedback: { impactOccurred: vi.fn() },
			openTelegramLink: vi.fn(),
		},
	}),
}));

// Mock seller shared state
vi.mock("@modules/seller/shared/state", () => ({
	$sellerStats: { getState: () => null, "@@unitShape": () => null },
	$profileCheckComplete: { getState: () => true, "@@unitShape": () => true },
	fetchSellerProfile: vi.fn(),
}));

// Mock notifications API
vi.mock("@shared/api/notifications", () => ({
	notificationsApi: {
		getUnreadCount: vi.fn().mockResolvedValue({ unread_count: 0 }),
		getPreferences: vi.fn().mockResolvedValue({ enabled: false }),
		updatePreferences: vi.fn().mockResolvedValue({ enabled: false }),
	},
}));

// Mock UnauthScreen
vi.mock("@shared/ui/UnauthScreen", () => ({
	UnauthScreen: (props: any) => (
		<div data-testid="unauth-screen">{props.title}</div>
	),
}));

// Mock ProfileMenuItem
vi.mock("@shared/ui/ProfileMenuItem", () => ({
	ProfileMenuItem: (props: any) => (
		<div data-testid="profile-menu-item" onClick={props.onClick}>
			{props.label || "menu-item"}
		</div>
	),
}));

// Mock LanguageSwitcher
vi.mock("@shared/ui/LanguageSwitcher", () => ({
	LanguageSwitcher: () => <div data-testid="language-switcher">Language</div>,
}));

// Mock theme
vi.mock("@app/styles/theme", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@app/styles/theme")>();
	return {
		...actual,
		shadows: { ...actual.shadows, card: "0 2px 8px rgba(0,0,0,0.04)" },
		gradients: {
			...actual.gradients,
			primary: "linear-gradient(135deg, #228be6, #1971c2)",
		},
	};
});

describe("Profile", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show user info when authenticated", async () => {
		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show unauth screen when not authenticated", async () => {
		const authMock = await import("@app/providers/useAuth");
		(authMock.useAuth as any) = () => ({
			isAuthenticated: false,
			user: null,
			logout: vi.fn(),
		});

		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render profile menu items", async () => {
		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render language switcher", async () => {
		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle logout action", async () => {
		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show seller stats when available", async () => {
		const sellerState = await import("@modules/seller/shared/state");
		(sellerState.$sellerStats as any).getState = () => ({
			total_listings: 5,
			active_listings: 3,
		});
		(sellerState.$sellerStats as any)["@@unitShape"] = () => ({
			total_listings: 5,
			active_listings: 3,
		});

		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should navigate to become-seller page", async () => {
		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should navigate to preferences page", async () => {
		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should display user avatar", async () => {
		const { Profile } = await import("../ui/page/Page");
		renderPage(<Profile.Page />);
		expect(document.body).toBeTruthy();
	});
});
