import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

// Mock crawled model
vi.mock("../model", () => ({
	pageOpened: vi.fn(),
	sourceChanged: vi.fn(),
	pageChanged: vi.fn(),
	propertyTypeChanged: vi.fn(),
	listingTypeChanged: vi.fn(),
	resetCrawledState: vi.fn(),
	fetchCrawledStatsFx: vi.fn(),
	$crawledStats: {
		getState: () => ({ olx_count: 120, telegram_count: 80 }),
		"@@unitShape": () => ({ olx_count: 120, telegram_count: 80 }),
	},
	$activeSource: { getState: () => "all", "@@unitShape": () => "all" },
	$crawledPage: { getState: () => 1, "@@unitShape": () => 1 },
	$propertyType: { getState: () => null, "@@unitShape": () => null },
	$listingType: { getState: () => null, "@@unitShape": () => null },
	$olxListings: { getState: () => [], "@@unitShape": () => [] },
	$telegramListings: { getState: () => [], "@@unitShape": () => [] },
	$olxTotal: { getState: () => 0, "@@unitShape": () => 0 },
	$telegramTotal: { getState: () => 0, "@@unitShape": () => 0 },
	$olxTotalPages: { getState: () => 1, "@@unitShape": () => 1 },
	$telegramTotalPages: { getState: () => 1, "@@unitShape": () => 1 },
	$isLoadingCrawled: { getState: () => false, "@@unitShape": () => false },
	$isLoadingCrawledStats: { getState: () => false, "@@unitShape": () => false },
	$crawledError: { getState: () => null, "@@unitShape": () => null },
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
				"crawled.title": "Crawled Data",
				"crawled.subtitle": "Listings from external sources",
				"crawled.noListingsFound": "No crawled listings found",
				"crawled.apartment": "Apartment",
				"crawled.house": "House",
				"crawled.commercial": "Commercial",
				"crawled.land": "Land",
				"common.allSources": "All Sources",
				"common.allTypes": "All Types",
				"common.tryAdjustingFilters": "Try adjusting your filters",
			};
			if (key === "crawled.totalListings" && opts)
				return `Total: ${opts.count} listings`;
			return map[key] || key;
		},
		i18n: { language: "en" },
	}),
}));

// Mock shared dependencies
vi.mock("@shared/lib/date", () => ({
	formatTimeAgo: (_d: string) => "2 hours ago",
}));

vi.mock("@app/styles/theme", () => ({
	formatPrice: (price: number, _currency: string) => `$${price}`,
}));

vi.mock("@shared/lib/regions", () => ({
	translateDistrict: (key: string) => key,
}));

// Mock CSS
vi.mock("@modules/admin/shared/ui/admin.css", () => ({}));

describe("AdminCrawled", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeleton when isLoading is true", async () => {
		const model = await import("../model");
		(model.$isLoadingCrawled as any).getState = () => true;
		(model.$isLoadingCrawled as any)["@@unitShape"] = () => true;

		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(document.querySelector(".admin-skeleton-card")).toBeTruthy();
	});

	it("should display OLX and Telegram stats cards", async () => {
		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(screen.getByText("OLX.uz")).toBeTruthy();
		expect(screen.getByText("Telegram")).toBeTruthy();
	});

	it("should display OLX count in stats", async () => {
		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(screen.getByText("120")).toBeTruthy();
	});

	it("should display Telegram count in stats", async () => {
		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(screen.getByText("80")).toBeTruthy();
	});

	it("should render source tab filters", async () => {
		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(screen.getByText("All Sources")).toBeTruthy();
	});

	it("should render property type filters", async () => {
		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(screen.getByText("All Types")).toBeTruthy();
		expect(screen.getByText("Apartment")).toBeTruthy();
		expect(screen.getByText("House")).toBeTruthy();
	});

	it("should display page title", async () => {
		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(screen.getByText("Crawled Data")).toBeTruthy();
		expect(screen.getByText("Listings from external sources")).toBeTruthy();
	});

	it("should show empty state when no listings", async () => {
		const model = await import("../model");
		(model.$olxListings as any).getState = () => [];
		(model.$olxListings as any)["@@unitShape"] = () => [];
		(model.$telegramListings as any).getState = () => [];
		(model.$telegramListings as any)["@@unitShape"] = () => [];
		(model.$isLoadingCrawled as any).getState = () => false;
		(model.$isLoadingCrawled as any)["@@unitShape"] = () => false;

		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(screen.getByText("No crawled listings found")).toBeTruthy();
	});

	it("should call pageOpened on mount", async () => {
		const model = await import("../model");
		const { AdminCrawled } = await import("../ui/page/Page");
		renderPage(<AdminCrawled.Page />);
		expect(model.pageOpened).toBeDefined();
	});
});
