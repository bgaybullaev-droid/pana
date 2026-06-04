import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

const mockEditingListing = {
	id: "listing-1",
	title: "Existing Apartment",
	description: "A nice apartment",
	price: 75000,
	currency: "USD",
	type: "sell",
	property_type: "apartment",
	rooms: 3,
	area: 90,
	floor: 5,
	total_floors: 9,
	region: "tashkent",
	district: "chilanzar",
	address: "123 Main St",
	phone: "+998901234567",
	status: "active",
	images: [
		{
			id: "img-1",
			original_url: "https://example.com/img1.jpg",
			medium_url: "https://example.com/img1-m.jpg",
		},
	],
};

// Mock shared listing state
vi.mock("@shared/state/listing/model", () => ({
	fetchListingForEdit: vi.fn(),
	updateListing: vi.fn(),
	updateListingFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
		doneData: { watch: vi.fn(() => vi.fn()) },
		failData: { watch: vi.fn(() => vi.fn()) },
		done: { watch: vi.fn(() => vi.fn()) },
		fail: { watch: vi.fn(() => vi.fn()) },
	},
	$editingListing: {
		getState: () => mockEditingListing,
		"@@unitShape": () => mockEditingListing,
	},
	$isLoadingEdit: { getState: () => false, "@@unitShape": () => false },
	$isUpdating: { getState: () => false, "@@unitShape": () => false },
	$editError: { getState: () => null, "@@unitShape": () => null },
	resetEditState: vi.fn(),
	fetchListingSourceTextFx: vi.fn().mockResolvedValue(null),
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

// Mock Telegram WebApp
vi.mock("@app/providers/useTelegram", () => ({
	useTelegram: () => ({
		webApp: {
			HapticFeedback: { notificationOccurred: vi.fn() },
		},
	}),
}));

// Mock useEffectorNotification
vi.mock("@shared/hooks/useEffectorNotification", () => ({
	useEffectorNotification: vi.fn(),
}));

// Mock FormSection
vi.mock("@shared/ui/FormSection", () => ({
	FormSection: ({ title, children }: any) => (
		<div data-testid="form-section">
			<span>{title}</span>
			{children}
		</div>
	),
}));

// Mock listing form hook
const mockFormSetValues = vi.fn();
vi.mock("@modules/seller/feature/listing-form/ui/useListingForm", () => ({
	useListingForm: () => ({
		form: {
			values: {
				type: "sell",
				property_type: "apartment",
				title: "Existing Apartment",
				description: "A nice apartment",
				price: 75000,
				currency: "USD",
				rooms: 3,
				area: 90,
				floor: 5,
				total_floors: 9,
				region: "tashkent",
				district: "chilanzar",
				address: "123 Main St",
				phone: "+998901234567",
			},
			errors: {},
			setValues: mockFormSetValues,
			getInputProps: (_field: string) => ({
				value: "",
				onChange: vi.fn(),
				error: undefined,
			}),
			validate: () => ({ hasErrors: false }),
			reset: vi.fn(),
			onSubmit: (handler: any) => (e?: any) => {
				e?.preventDefault?.();
				return handler;
			},
		},
		images: [],
		isUploading: false,
		uploadProgress: 0,
		regions: [{ value: "tashkent", label: "Tashkent" }],
		districts: [{ value: "chilanzar", label: "Chilanzar" }],
		handleRegionChange: vi.fn(),
		handleAddImages: vi.fn(),
		handleRemoveImage: vi.fn(),
		handleUploadImages: vi.fn().mockResolvedValue([]),
		buildListingData: vi.fn((values: any) => values),
		t: (key: string) => key,
	}),
}));

vi.mock("@modules/seller/feature/listing-form/ui/ListingFormFields", () => ({
	ListingFormFields: () => (
		<div data-testid="listing-form-fields">Form Fields</div>
	),
}));

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
	const actual = await vi.importActual("react-router-dom");
	return {
		...actual,
		useNavigate: () => mockNavigate,
		useParams: () => ({ id: "listing-1" }),
		useSearchParams: () => [new URLSearchParams(), vi.fn()],
		useLocation: () => ({
			pathname: "/edit/listing-1",
			search: "",
			hash: "",
			state: null,
		}),
	};
});

describe("EditListingPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { EditListing } = await import("../ui/page/Page");
		renderPage(<EditListing.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading skeletons when loading", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => true;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => true;

		const { EditListing } = await import("../ui/page/Page");
		const { container } = renderPage(<EditListing.Page />);
		expect(container.querySelector(".mantine-Skeleton-root")).toBeTruthy();
	});

	it("should display edit page title", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => false;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => false;

		const { EditListing } = await import("../ui/page/Page");
		renderPage(<EditListing.Page />);
		expect(screen.getByText("editListing.title")).toBeTruthy();
	});

	it("should render listing form fields for editing", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => false;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => false;

		const { EditListing } = await import("../ui/page/Page");
		renderPage(<EditListing.Page />);
		expect(screen.getByTestId("listing-form-fields")).toBeTruthy();
	});

	it("should call fetchListingForEdit on mount with listing id", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => false;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => false;

		const { EditListing } = await import("../ui/page/Page");
		renderPage(<EditListing.Page />);
		expect(model.fetchListingForEdit).toHaveBeenCalledWith("listing-1");
	});

	it("should display existing images section", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => false;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => false;
		(model.$editingListing as any).getState = () => mockEditingListing;
		(model.$editingListing as any)["@@unitShape"] = () => mockEditingListing;

		const { EditListing } = await import("../ui/page/Page");
		renderPage(<EditListing.Page />);
		expect(screen.getByText("editListing.currentPhotos")).toBeTruthy();
	});

	it("should display add new photos section", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => false;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => false;

		const { EditListing } = await import("../ui/page/Page");
		renderPage(<EditListing.Page />);
		expect(screen.getByText("editListing.addNewPhotos")).toBeTruthy();
	});

	it("should render save button", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => false;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => false;

		const { EditListing } = await import("../ui/page/Page");
		renderPage(<EditListing.Page />);
		expect(screen.getByText("editListing.save")).toBeTruthy();
	});

	it("should have back navigation button", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => false;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => false;

		const { EditListing } = await import("../ui/page/Page");
		const { container } = renderPage(<EditListing.Page />);
		// Back button (ActionIcon with IconArrowLeft)
		const actionIcons = container.querySelectorAll(".mantine-ActionIcon-root");
		expect(actionIcons.length).toBeGreaterThan(0);
	});

	it("should display image count badge", async () => {
		const model = await import("@shared/state/listing/model");
		(model.$isLoadingEdit as any).getState = () => false;
		(model.$isLoadingEdit as any)["@@unitShape"] = () => false;
		(model.$editingListing as any).getState = () => mockEditingListing;
		(model.$editingListing as any)["@@unitShape"] = () => mockEditingListing;

		const { EditListing } = await import("../ui/page/Page");
		renderPage(<EditListing.Page />);
		// Badge shows count/10 format
		expect(screen.getByText("1/10")).toBeTruthy();
	});
});
