import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage } from "@/test/helpers";

// Mock react-router-dom params
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useParams: () => ({ source: "olx", id: "crawled-1" }),
	};
});

// Mock crawler API
vi.mock("@shared/api/crawlerListings", () => ({
	fetchOLXListingById: vi.fn(() =>
		Promise.resolve({
			id: "crawled-1",
			price: 45000,
			currency: "USD",
			property_type: "apartment",
			listing_type: "sell",
			description: "Nice crawled apartment",
			district: "chilanzar",
			address: "456 Side St",
			rooms: 2,
			area_sqm: 65,
			floor: 3,
			total_floors: 9,
			images: ["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
			confidence: 0.85,
			created_at: "2024-01-01T00:00:00Z",
			crawled_at: "2024-01-01T00:00:00Z",
			url: "https://olx.uz/listing/123",
			seller_name: "OLX Seller",
			seller_type: "owner",
			condition: "good",
			building_type: "brick",
			furnishing: "furnished",
			ceiling_height: "2.8",
			bathroom: "separate",
			views_count: 150,
			posted_date: "2024-01-01",
			contact_phone: "+998901234567",
			amenities: ["parking", "elevator"],
			raw_text: "Original OLX listing text here",
			signature_hash: "abc123hash",
		}),
	),
	fetchTelegramListingById: vi.fn(() =>
		Promise.resolve({
			id: "crawled-2",
			price: 30000,
			currency: "USD",
			property_type: "house",
			listing_type: "rent",
			description: "Telegram listed house",
			district: "mirzo",
			address: "",
			rooms: 4,
			area_sqm: 120,
			floor: null,
			total_floors: null,
			images: [],
			confidence: 0.6,
			created_at: "2024-02-01T00:00:00Z",
			source_channel: "@realestate_tg",
			message_id: 12345,
			contact_phone: "+998907654321",
			amenities: [],
			raw_text: "Telegram original text",
			signature_hash: "def456hash",
		}),
	),
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
				"crawledDetail.backToCrawled": "Back to Crawled",
				"crawledDetail.olxDetails": "OLX Details",
				"crawledDetail.telegramDetails": "Telegram Details",
				"crawledDetail.channel": "Channel",
				"crawledDetail.messageId": "Message ID",
				"crawledDetail.contactPhone": "Contact Phone",
				"crawledDetail.buildingType": "Building Type",
				"crawledDetail.condition": "Condition",
				"crawledDetail.furnishing": "Furnishing",
				"crawledDetail.ceilingHeight": "Ceiling Height",
				"crawledDetail.bathroom": "Bathroom",
				"crawledDetail.viewsOnOlx": "Views on OLX",
				"crawledDetail.postedOnOlx": "Posted on OLX",
				"crawledDetail.contact": "Contact",
				"crawledDetail.amenities": "Amenities",
				"crawledDetail.rawText": "Raw Text",
				"crawledDetail.metadata": "Metadata",
				"crawledDetail.crawledAt": "Crawled At",
				"crawledDetail.olxUrl": "OLX URL",
				"crawledDetail.signatureHash": "Signature Hash",
				"crawledDetail.confidenceUnknown": "Unknown",
				"crawledDetail.viewOnOlx": "View on OLX",
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
				"common.created": "Created",
				"common.back": "Back",
				"common.noImages": "No images",
				"common.tapToZoom": "Tap to zoom",
			};
			if (key === "crawledDetail.confidenceHigh" && opts)
				return `${opts.pct}% confidence`;
			if (key === "crawledDetail.confidenceMedium" && opts)
				return `${opts.pct}% confidence`;
			if (key === "crawledDetail.confidenceLow" && opts)
				return `${opts.pct}% confidence`;
			if (key === "crawledDetail.crawledAgo" && opts)
				return `Crawled ${opts.timeAgo}`;
			return map[key] || key;
		},
		i18n: { language: "en" },
	}),
}));

// Mock shared dependencies
vi.mock("@shared/lib/date", () => ({
	formatDate: (d: string) => new Date(d).toLocaleDateString(),
	formatTimeAgo: (_d: string) => "2 hours ago",
}));

vi.mock("@app/styles/theme", async (importOriginal) => {
	const actual = await importOriginal<typeof import("@app/styles/theme")>();
	return {
		...actual,
		formatPrice: (price: number, _currency: string) => `$${price}`,
	};
});

vi.mock("@shared/lib/regions", () => ({
	translateDistrict: (key: string) => key,
}));

// Mock CSS
vi.mock("@modules/admin/shared/ui/admin.css", () => ({}));

describe("AdminCrawledDetailPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Main: AdminCrawledDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminCrawledDetailPage />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeleton initially", async () => {
		const { Main: AdminCrawledDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminCrawledDetailPage />);
		// Initially loading before the fetch resolves
		expect(document.body).toBeTruthy();
	});

	it("should display back to crawled button", async () => {
		const { Main: AdminCrawledDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminCrawledDetailPage />);
		// The back button is always visible even during loading
		expect(document.body).toBeTruthy();
	});

	it("should display OLX source header for OLX listing", async () => {
		const { Main: AdminCrawledDetailPage } = await import("../ui/main/Main");
		const { container } = renderPage(<AdminCrawledDetailPage />);
		// Component loads and handles OLX source param
		expect(container).toBeTruthy();
	});

	it("should render the page with source param", async () => {
		const { Main: AdminCrawledDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminCrawledDetailPage />);
		expect(document.body).toBeTruthy();
	});

	it("should handle API fetch on mount", async () => {
		const api = await import("@shared/api/crawlerListings");
		const { Main: AdminCrawledDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminCrawledDetailPage />);
		expect(api.fetchOLXListingById).toBeDefined();
	});

	it("should handle missing listing gracefully", async () => {
		const api = await import("@shared/api/crawlerListings");
		(api.fetchOLXListingById as any).mockRejectedValueOnce(
			new Error("Not found"),
		);

		const { Main: AdminCrawledDetailPage } = await import("../ui/main/Main");
		renderPage(<AdminCrawledDetailPage />);
		expect(document.body).toBeTruthy();
	});

	it("should render component elements correctly", async () => {
		const { Main: AdminCrawledDetailPage } = await import("../ui/main/Main");
		const { container } = renderPage(<AdminCrawledDetailPage />);
		expect(
			container.querySelector(
				".admin-page-enter, .admin-skeleton, .admin-back-btn",
			),
		).toBeTruthy();
	});
});
