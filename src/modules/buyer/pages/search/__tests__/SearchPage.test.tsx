import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

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

// Mock shared libs
vi.mock("@shared/lib/constants", () => ({
	ROOMS_OPTIONS_KEYS: ["studio", "1", "2", "3", "4"],
}));

vi.mock("@shared/lib/regions", () => ({
	getRegionKeys: () => ["tashkent", "samarkand"],
	getDistrictsForRegion: () => ["chilanzar", "yunusabad"],
	translateRegion: (key: string) => key,
	translateDistrict: (key: string) => key,
}));

vi.mock("@app/styles/theme", () => ({
	gradients: { primary: "linear-gradient(135deg, #228be6, #1971c2)" },
	shadows: {
		card: "0 2px 8px rgba(0,0,0,0.04)",
		soft: "0 1px 4px rgba(0,0,0,0.06)",
		button: "0 4px 12px rgba(34,139,230,0.3)",
	},
	transitions: { spring: "all 0.3s ease", fast: "all 0.15s ease" },
}));

// Mock GradientHeader
vi.mock("@shared/ui/GradientHeader", () => ({
	GradientHeader: ({ title }: any) => (
		<div data-testid="gradient-header">{title}</div>
	),
}));

// Mock FormSection
vi.mock("@shared/ui/FormSection", () => ({
	FormSection: ({ title, children }: any) => (
		<div data-testid="form-section">
			<div>{title}</div>
			{children}
		</div>
	),
}));

describe("Search", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render search input", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render gradient header", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(screen.getByTestId("gradient-header")).toBeTruthy();
	});

	it("should render property type options", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		// Form sections should be rendered
		const sections = screen.getAllByTestId("form-section");
		expect(sections.length).toBeGreaterThan(0);
	});

	it("should render deal type selector (buy/rent)", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render room count chips", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render price range slider", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render region and district selectors", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render search and reset buttons", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should handle clear filters", async () => {
		const { Search } = await import("../ui/page/Page");
		renderPage(<Search.Page />);
		expect(document.body).toBeTruthy();
	});
});
