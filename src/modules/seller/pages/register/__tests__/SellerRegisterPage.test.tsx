import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

// Mock seller shared state
vi.mock("@modules/seller/shared/state", () => ({
	$sellerProfile: { getState: () => null, "@@unitShape": () => null },
	$isLoadingProfile: { getState: () => false, "@@unitShape": () => false },
	$sellerError: { getState: () => null, "@@unitShape": () => null },
	registerAsSeller: vi.fn(),
	registerAsSellerFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
		doneData: { watch: vi.fn(() => vi.fn()) },
		failData: { watch: vi.fn(() => vi.fn()) },
		done: { watch: vi.fn(() => vi.fn()) },
		fail: { watch: vi.fn(() => vi.fn()) },
	},
}));

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

// Mock useEffectorNotification
vi.mock("@shared/hooks/useEffectorNotification", () => ({
	useEffectorNotification: vi.fn(),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useNavigate: () => mockNavigate,
		useParams: () => ({}),
		useSearchParams: () => [new URLSearchParams(), vi.fn()],
		useLocation: () => ({
			pathname: "/seller/register",
			search: "",
			hash: "",
			state: null,
		}),
	};
});

describe("SellerRegisterPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should display registration title", async () => {
		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(screen.getByText("register.title")).toBeTruthy();
		expect(screen.getByText("register.subtitle")).toBeTruthy();
	});

	it("should render phone input field", async () => {
		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(screen.getByText("register.phone")).toBeTruthy();
	});

	it("should render company name input field", async () => {
		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(screen.getByText("register.companyName")).toBeTruthy();
	});

	it("should display benefits section", async () => {
		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(screen.getByText("register.benefits")).toBeTruthy();
		expect(screen.getByText("register.benefitListingsTitle")).toBeTruthy();
		expect(screen.getByText("register.benefitAnalyticsTitle")).toBeTruthy();
		expect(screen.getByText("register.benefitLeadsTitle")).toBeTruthy();
	});

	it("should render submit button", async () => {
		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(screen.getByText("register.submit")).toBeTruthy();
	});

	it("should show loading overlay when registering", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$isLoadingProfile as any).getState = () => true;
		(state.$isLoadingProfile as any)["@@unitShape"] = () => true;

		const { SellerRegister } = await import("../ui/page/Page");
		const { container } = renderPage(<SellerRegister.Page />);
		expect(
			container.querySelector(".mantine-LoadingOverlay-root"),
		).toBeTruthy();
	});

	it("should display terms text", async () => {
		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(screen.getByText("register.terms")).toBeTruthy();
	});

	it("should redirect if already registered as seller", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$sellerProfile as any).getState = () => ({
			company_name: "Existing",
			phone: "+998901234567",
		});
		(state.$sellerProfile as any)["@@unitShape"] = () => ({
			company_name: "Existing",
			phone: "+998901234567",
		});

		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(mockNavigate).toHaveBeenCalledWith("/seller/dashboard");
	});

	it("should display form section title", async () => {
		const state = await import("@modules/seller/shared/state");
		(state.$sellerProfile as any).getState = () => null;
		(state.$sellerProfile as any)["@@unitShape"] = () => null;

		const { SellerRegister } = await import("../ui/page/Page");
		renderPage(<SellerRegister.Page />);
		expect(screen.getByText("register.formTitle")).toBeTruthy();
	});
});
