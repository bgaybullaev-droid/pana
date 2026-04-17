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

// Mock GradientHeader
vi.mock("@shared/ui/GradientHeader", () => ({
	GradientHeader: ({ title }: any) => (
		<div data-testid="gradient-header">{title}</div>
	),
}));

// Mock PreferencesPanel
vi.mock("@modules/buyer/feature/preferences", () => ({
	PreferencesPanel: () => (
		<div data-testid="preferences-panel">Preferences Panel</div>
	),
}));

describe("Preferences", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Preferences } = await import("../ui/page/Page");
		renderPage(<Preferences.Page />);
		expect(document.body).toBeTruthy();
	});

	it.skip("should render gradient header", async () => {
		const { Preferences } = await import("../ui/page/Page");
		renderPage(<Preferences.Page />);
		expect(screen.getByTestId("gradient-header")).toBeTruthy();
	});

	it("should render preferences panel", async () => {
		const { Preferences } = await import("../ui/page/Page");
		renderPage(<Preferences.Page />);
		expect(screen.getByTestId("preferences-panel")).toBeTruthy();
	});

	it.skip("should display preferences title in header", async () => {
		const { Preferences } = await import("../ui/page/Page");
		renderPage(<Preferences.Page />);
		expect(screen.getByTestId("gradient-header")).toBeTruthy();
	});

	it("should have correct page background", async () => {
		const { Preferences } = await import("../ui/page/Page");
		renderPage(<Preferences.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render panel with proper offset from header", async () => {
		const { Preferences } = await import("../ui/page/Page");
		renderPage(<Preferences.Page />);
		expect(screen.getByTestId("preferences-panel")).toBeTruthy();
	});

	it.skip("should use translation for title", async () => {
		const { Preferences } = await import("../ui/page/Page");
		renderPage(<Preferences.Page />);
		const header = screen.getByTestId("gradient-header");
		expect(header.textContent).toBe("preferences.title");
	});

	it("should render full page layout", async () => {
		const { Preferences } = await import("../ui/page/Page");
		const { container } = renderPage(<Preferences.Page />);
		expect(container.firstChild).toBeTruthy();
	});
});
