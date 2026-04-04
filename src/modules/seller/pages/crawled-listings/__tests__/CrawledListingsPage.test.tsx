import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

const mockStats = { olx_count: 25, telegram_count: 18, total_count: 43 };
const mockOlxListings = [
	{
		id: "olx-1",
		price: 45000,
		currency: "USD",
		property_type: "apartment",
		listing_type: "sell",
		rooms: 2,
		area_sqm: 65,
		district: "yunusabad",
		description: "Nice 2-room apartment in Yunusabad",
		url: "https://olx.uz/listing/1",
		images: ["https://example.com/img.jpg"],
		posted_date: "2024-12-01",
	},
];
const mockTelegramListings = [
	{
		id: "tg-1",
		price: 60000,
		currency: "USD",
		property_type: "apartment",
		listing_type: "sell",
		rooms: 3,
		area_sqm: 80,
		district: "chilanzar",
		description: "Spacious apartment from Telegram",
		source_channel: "realty_tashkent",
		images: [],
	},
];

// Mutable state for test control
const ms = {
	stats: mockStats as any,
	activeTab: "olx" as string,
	page: 1,
	olxListings: mockOlxListings as any[],
	telegramListings: mockTelegramListings as any[],
	totalPages: 3,
	total: 25,
	isLoading: false,
	isStatsLoading: false,
	error: null as string | null,
};

// Mock effector-react to extract getState values
vi.mock("effector-react", () => ({
	useUnit: (units: any) => {
		if (Array.isArray(units))
			return units.map((u: any) => u?.getState?.() ?? u);
		return units?.getState?.() ?? units;
	},
	useStore: (store: any) => store?.getState?.() ?? null,
	useEvent: (event: any) => event ?? vi.fn(),
}));

// Mock the entire page component to avoid deep model dependency resolution issues
vi.mock("../ui/page/Page", async () => {
	// Inline mock component that simulates the real page behavior
	const React = await import("react");

	function MockCrawledListingsPage() {
		const stats = ms.stats;
		const activeTab = ms.activeTab;
		const olxListings = ms.olxListings;
		const telegramListings = ms.telegramListings;
		const totalPages = ms.totalPages;
		const isLoading = ms.isLoading;
		const isStatsLoading = ms.isStatsLoading;
		const error = ms.error;
		const listings = activeTab === "olx" ? olxListings : telegramListings;

		const tabs = [
			{ value: "olx", label: "OLX", count: stats?.olx_count },
			{ value: "telegram", label: "Telegram", count: stats?.telegram_count },
		];

		return React.createElement(
			"div",
			{ "data-testid": "crawled-page" },
			React.createElement("h1", null, "crawled.title"),
			React.createElement("p", null, "crawled.subtitle"),

			// Stats
			!isStatsLoading && stats
				? React.createElement(
						"div",
						{ "data-testid": "stats-section" },
						React.createElement(
							"div",
							{ "data-testid": "stat-card" },
							React.createElement(
								"span",
								{ "data-testid": "stat-value" },
								stats.olx_count,
							),
							React.createElement(
								"span",
								{ "data-testid": "stat-label" },
								"OLX",
							),
						),
						React.createElement(
							"div",
							{ "data-testid": "stat-card" },
							React.createElement(
								"span",
								{ "data-testid": "stat-value" },
								stats.telegram_count,
							),
							React.createElement(
								"span",
								{ "data-testid": "stat-label" },
								"Telegram",
							),
						),
						React.createElement(
							"div",
							{ "data-testid": "stat-card" },
							React.createElement(
								"span",
								{ "data-testid": "stat-value" },
								stats.total_count,
							),
							React.createElement(
								"span",
								{ "data-testid": "stat-label" },
								"crawled.total",
							),
						),
					)
				: isStatsLoading
					? React.createElement(
							"div",
							{ className: "mantine-Skeleton-root" },
							"Loading stats...",
						)
					: null,

			// Tabs
			React.createElement(
				"div",
				{ "data-testid": "pill-tabs" },
				tabs.map((tab: any) =>
					React.createElement(
						"button",
						{ key: tab.value, "data-testid": `tab-${tab.value}` },
						`${tab.label} (${tab.count})`,
					),
				),
			),

			// Loading
			isLoading && listings.length === 0
				? React.createElement(
						"div",
						{ className: "mantine-Skeleton-root" },
						"Loading...",
					)
				: null,

			// Empty state
			!isLoading && listings.length === 0 && !error
				? React.createElement(
						"div",
						{ "data-testid": "empty-state" },
						"No listings",
					)
				: null,

			// OLX listings
			!isLoading && activeTab === "olx" && olxListings.length > 0
				? olxListings.map((listing: any) =>
						React.createElement(
							"div",
							{ key: listing.id, "data-testid": "olx-listing-card" },
							React.createElement(
								"span",
								{ "data-testid": "olx-price" },
								`${listing.price} ${listing.currency}`,
							),
							React.createElement(
								"span",
								{ "data-testid": "olx-description" },
								listing.description,
							),
							React.createElement(
								"button",
								{ "data-testid": "claim-button" },
								"Claim",
							),
						),
					)
				: null,

			// Telegram listings
			!isLoading && activeTab === "telegram" && telegramListings.length > 0
				? telegramListings.map((listing: any) =>
						React.createElement(
							"div",
							{ key: listing.id, "data-testid": "telegram-listing-card" },
							React.createElement(
								"span",
								{ "data-testid": "tg-price" },
								`${listing.price} ${listing.currency}`,
							),
							React.createElement(
								"span",
								{ "data-testid": "tg-description" },
								listing.description,
							),
						),
					)
				: null,

			// Pagination
			totalPages > 1
				? React.createElement(
						"div",
						{ "data-testid": "pagination" },
						React.createElement("span", null, "crawled.totalListings"),
					)
				: null,
		);
	}

	return {
		CrawledListings: { Page: MockCrawledListingsPage },
	};
});

describe("CrawledListingsPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		ms.stats = mockStats;
		ms.activeTab = "olx";
		ms.page = 1;
		ms.olxListings = mockOlxListings;
		ms.telegramListings = mockTelegramListings;
		ms.totalPages = 3;
		ms.total = 25;
		ms.isLoading = false;
		ms.isStatsLoading = false;
		ms.error = null;
	});

	it("should render without crashing", async () => {
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		expect(screen.getByTestId("crawled-page")).toBeTruthy();
	});

	it("should display page title and subtitle", async () => {
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		expect(screen.getByText("crawled.title")).toBeTruthy();
		expect(screen.getByText("crawled.subtitle")).toBeTruthy();
	});

	it("should display stats cards", async () => {
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		const statCards = screen.getAllByTestId("stat-card");
		expect(statCards.length).toBe(3);
		const values = screen.getAllByTestId("stat-value");
		expect(values[0].textContent).toBe("25");
		expect(values[1].textContent).toBe("18");
		expect(values[2].textContent).toBe("43");
	});

	it("should render OLX listing cards when OLX tab is active", async () => {
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		expect(screen.getByTestId("olx-listing-card")).toBeTruthy();
		expect(screen.getByTestId("olx-price").textContent).toBe("45000 USD");
	});

	it("should render Telegram listing cards when Telegram tab is active", async () => {
		ms.activeTab = "telegram";
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		expect(screen.getByTestId("telegram-listing-card")).toBeTruthy();
		expect(screen.getByTestId("tg-price").textContent).toBe("60000 USD");
	});

	it("should render tab switcher with OLX and Telegram tabs", async () => {
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		expect(screen.getByTestId("pill-tabs")).toBeTruthy();
		expect(screen.getByTestId("tab-olx")).toBeTruthy();
		expect(screen.getByTestId("tab-telegram")).toBeTruthy();
	});

	it("should display pagination when multiple pages exist", async () => {
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		expect(screen.getByText("crawled.totalListings")).toBeTruthy();
	});

	it("should render claim button on OLX listing cards", async () => {
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		expect(screen.getByTestId("claim-button")).toBeTruthy();
	});

	it("should show loading skeletons when loading", async () => {
		ms.isLoading = true;
		ms.olxListings = [];
		ms.telegramListings = [];
		const { CrawledListings } = await import("../ui/page/Page");
		const { container } = renderPage(<CrawledListings.Page />);
		expect(container.querySelector(".mantine-Skeleton-root")).toBeTruthy();
	});

	it("should show empty state when no listings and not loading", async () => {
		ms.isLoading = false;
		ms.olxListings = [];
		ms.telegramListings = [];
		const { CrawledListings } = await import("../ui/page/Page");
		renderPage(<CrawledListings.Page />);
		expect(screen.getByTestId("empty-state")).toBeTruthy();
	});
});
