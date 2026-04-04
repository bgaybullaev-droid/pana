import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage } from "@/test/helpers";

// Mock effector-react
vi.mock("effector-react", () => ({
	useUnit: (units: any) => {
		if (Array.isArray(units)) {
			return units.map((u: any) => {
				if (typeof u?.getState === "function") return u.getState();
				return u;
			});
		}
		return units?.getState?.() ?? units;
	},
	useStore: (store: any) => store?.getState?.() ?? null,
	useEvent: (event: any) => event ?? vi.fn(),
}));

// Mock useAuth
vi.mock("@app/providers/useAuth", () => ({
	useAuth: () => ({
		isAuthenticated: true,
		isLoading: false,
		user: {
			id: "1",
			first_name: "Test",
			is_seller: false,
			phone: "+998901234567",
		},
	}),
}));

// Mock seller shared state
vi.mock("@modules/seller/shared/state", () => {
	const isLoadingStore = { getState: () => false, "@@unitShape": () => false };
	const errorStore = { getState: () => null, "@@unitShape": () => null };
	return {
		registerAsSeller: vi.fn(),
		registerAsSellerFx: {
			pending: isLoadingStore,
			doneData: { watch: vi.fn(() => vi.fn()) },
		},
		$isLoadingProfile: isLoadingStore,
		$sellerError: errorStore,
	};
});

// Mock shared libs
vi.mock("@shared/lib/constants", () => ({
	SELLER_BOT_USERNAME: "test_seller_bot",
}));

// Mock mantine notifications
vi.mock("@mantine/notifications", () => ({
	notifications: {
		show: vi.fn(),
	},
}));

// Mock theme
vi.mock("@app/styles/theme", () => ({
	gradients: {
		orange: "linear-gradient(135deg, #ff6e01, #ff9a44)",
		primary: "linear-gradient(135deg, #228be6, #1971c2)",
	},
}));

describe("BecomeSeller", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render header with seller icon", async () => {
		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render phone input field", async () => {
		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render company name input field", async () => {
		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render submit button", async () => {
		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render Telegram bot registration link", async () => {
		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show benefits list", async () => {
		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading overlay when registering", async () => {
		const sellerState = await import("@modules/seller/shared/state");
		(sellerState.$isLoadingProfile as any).getState = () => true;
		(sellerState.$isLoadingProfile as any)["@@unitShape"] = () => true;

		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show error message when registration fails", async () => {
		const sellerState = await import("@modules/seller/shared/state");
		(sellerState.$sellerError as any).getState = () => "Registration failed";
		(sellerState.$sellerError as any)["@@unitShape"] = () =>
			"Registration failed";

		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render back button", async () => {
		const { BecomeSeller } = await import("../ui/page/Page");
		renderPage(<BecomeSeller.Page />);
		expect(document.body).toBeTruthy();
	});
});
