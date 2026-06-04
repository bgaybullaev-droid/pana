import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen } from "@/test/helpers";

// Mock shared listing state
vi.mock("@shared/state/listing/model", () => ({
	createListing: vi.fn(),
	createListingFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
		doneData: { watch: vi.fn(() => vi.fn()) },
		failData: { watch: vi.fn(() => vi.fn()) },
		done: { watch: vi.fn(() => vi.fn()) },
		fail: { watch: vi.fn(() => vi.fn()) },
	},
	$isCreating: { getState: () => false, "@@unitShape": () => false },
	$createError: { getState: () => null, "@@unitShape": () => null },
	resetCreateState: vi.fn(),
	createDraftListingFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
		doneData: { watch: vi.fn(() => vi.fn()) },
		done: { watch: vi.fn(() => vi.fn()) },
		fail: { watch: vi.fn(() => vi.fn()) },
		failData: { watch: vi.fn(() => vi.fn()) },
	},
	fetchDraftPreviewFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
		doneData: { watch: vi.fn(() => vi.fn()) },
		done: { watch: vi.fn(() => vi.fn()) },
		fail: { watch: vi.fn(() => vi.fn()) },
	},
	publishDraftFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
		doneData: { watch: vi.fn(() => vi.fn()) },
		done: { watch: vi.fn(() => vi.fn()) },
		fail: { watch: vi.fn(() => vi.fn()) },
	},
	regenerateDraftFx: {
		pending: { getState: () => false, "@@unitShape": () => false },
		doneData: { watch: vi.fn(() => vi.fn()) },
		done: { watch: vi.fn(() => vi.fn()) },
		fail: { watch: vi.fn(() => vi.fn()) },
	},
}));

// Mock the local create-listing model stores and events to prevent Effector
// from executing store.on(createDraftListingFx.doneData, ...) with fake mocks.
vi.mock("../model/stores", () => ({
	$draftFormData: { getState: () => null, "@@unitShape": () => null },
	$draftId: { getState: () => null, "@@unitShape": () => null },
	$editedDescriptions: {
		getState: () => ({ ru: "", uz: "", uz_cyrl: "" }),
		"@@unitShape": () => ({ ru: "", uz: "", uz_cyrl: "" }),
	},
	$isCreatingDraft: { getState: () => false, "@@unitShape": () => false },
	$isPolling: { getState: () => false, "@@unitShape": () => false },
	$isRegenerating: { getState: () => false, "@@unitShape": () => false },
	$pollingTimedOut: { getState: () => false, "@@unitShape": () => false },
	$isPublishing: { getState: () => false, "@@unitShape": () => false },
	$draftPreview: { getState: () => null, "@@unitShape": () => null },
	$stage: { getState: () => 1, "@@unitShape": () => 1 },
	$aiGenStatus: { getState: () => "idle", "@@unitShape": () => "idle" },
}));

vi.mock("../model/events", () => ({
	stageAdvance: vi.fn(),
	stageBackToParams: vi.fn(),
	resetDraftFlow: vi.fn(),
	startAiGeneration: vi.fn(),
	editDescription: vi.fn(),
	setAiGenStatus: vi.fn(),
	pollingTimedOut: vi.fn(),
}));

// Prevent connections/index.ts (sample wiring) from executing with fake mocks.
vi.mock("../model/connections", () => ({}));

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
			<span data-testid="form-section-title">{title}</span>
			{children}
		</div>
	),
}));

// Mock listing form hook and fields
vi.mock("@modules/seller/feature/listing-form/ui/useListingForm", () => ({
	useListingForm: () => ({
		form: {
			values: {
				type: "sell",
				property_type: "apartment",
				title: "",
				description: "",
				price: 0,
				currency: "USD",
				rooms: undefined,
				area: undefined,
				floor: undefined,
				total_floors: undefined,
				region: "",
				district: "",
				address: "",
				phone: "",
			},
			errors: {},
			setValues: vi.fn(),
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
	ListingFormFields: ({ form: _form }: any) => (
		<div data-testid="listing-form-fields">
			<input
				data-testid="field-title"
				placeholder="createListing.titlePlaceholder"
			/>
			<input
				data-testid="field-price"
				placeholder="createListing.pricePlaceholder"
				type="number"
			/>
			<select data-testid="field-type">
				<option value="sell">sell</option>
				<option value="rent">rent</option>
			</select>
			<select data-testid="field-property-type">
				<option value="apartment">apartment</option>
				<option value="house">house</option>
				<option value="commercial">commercial</option>
				<option value="land">land</option>
			</select>
			<input data-testid="field-rooms" placeholder="rooms" type="number" />
			<select data-testid="field-region">
				<option value="tashkent">Tashkent</option>
			</select>
			<select data-testid="field-district">
				<option value="chilanzar">Chilanzar</option>
			</select>
			<input data-testid="field-phone" placeholder="phone" />
			<input data-testid="field-area" placeholder="area" type="number" />
			<input data-testid="field-description" placeholder="description" />
		</div>
	),
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
			pathname: "/create",
			search: "",
			hash: "",
			state: null,
		}),
	};
});

describe("CreateListingPage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should display page title", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByText("createListing.title")).toBeTruthy();
	});

	it("should render listing form fields", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByTestId("listing-form-fields")).toBeTruthy();
	});

	it("should render title input field", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByTestId("field-title")).toBeTruthy();
	});

	it("should render price input field", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByTestId("field-price")).toBeTruthy();
	});

	it("should render type selection (sell/rent)", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByTestId("field-type")).toBeTruthy();
	});

	it("should render property type selection", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByTestId("field-property-type")).toBeTruthy();
	});

	it("should render rooms input field", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByTestId("field-rooms")).toBeTruthy();
	});

	it("should render region and district selections", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByTestId("field-region")).toBeTruthy();
		expect(screen.getByTestId("field-district")).toBeTruthy();
	});

	it("should render image upload area (photos section)", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByText("createListing.addPhotos")).toBeTruthy();
		expect(screen.getByText("createListing.upTo10")).toBeTruthy();
	});

	it("should render phone input field", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByTestId("field-phone")).toBeTruthy();
	});

	it("should render submit/publish button", async () => {
		const { CreateListing } = await import("../ui/page/Page");
		renderPage(<CreateListing.Page />);
		expect(screen.getByText("createListing.nextButton")).toBeTruthy();
	});
});
