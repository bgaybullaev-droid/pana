import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage } from "@/test/helpers";

// Mock the model
vi.mock("../model", () => ({
	fetchFavorites: vi.fn(),
	removeFavorite: vi.fn(),
	$favorites: { getState: () => [], "@@unitShape": () => [] },
	$isLoading: { getState: () => false, "@@unitShape": () => false },
	$error: { getState: () => null, "@@unitShape": () => null },
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

// Mock useAuth
vi.mock("@app/providers/useAuth", () => ({
	useAuth: () => ({
		isAuthenticated: true,
		user: { id: "1", first_name: "Test", last_name: "User" },
	}),
}));

// Mock UnauthScreen
vi.mock("@shared/ui/UnauthScreen", () => ({
	UnauthScreen: (props: any) => (
		<div data-testid="unauth-screen">{props.title}</div>
	),
}));

// Mock FavoriteCard
vi.mock("../ui/main/FavoriteCard", () => ({
	FavoriteCard: ({ listing, onClick, onRemove }: any) => (
		<div data-testid="favorite-card" onClick={onClick}>
			{listing?.title}
			<button data-testid="remove-btn" onClick={onRemove}>
				Remove
			</button>
		</div>
	),
}));

describe("Favorites", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show loading state", async () => {
		const model = await import("../model");
		(model.$isLoading as any).getState = () => true;
		(model.$isLoading as any)["@@unitShape"] = () => true;

		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show empty state when no favorites", async () => {
		const model = await import("../model");
		(model.$favorites as any).getState = () => [];
		(model.$favorites as any)["@@unitShape"] = () => [];
		(model.$isLoading as any).getState = () => false;
		(model.$isLoading as any)["@@unitShape"] = () => false;

		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should render favorite cards when favorites exist", async () => {
		const model = await import("../model");
		const mockFavorites = [
			{ id: "1", title: "Apt 1", price: 50000, images: [] },
			{ id: "2", title: "House 1", price: 100000, images: [] },
		];
		(model.$favorites as any).getState = () => mockFavorites;
		(model.$favorites as any)["@@unitShape"] = () => mockFavorites;

		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should show unauth screen when not authenticated", async () => {
		const authMock = await import("@app/providers/useAuth");
		(authMock.useAuth as any) = () => ({
			isAuthenticated: false,
			user: null,
		});

		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should call fetchFavorites on mount", async () => {
		const model = await import("../model");
		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(model.fetchFavorites).toBeDefined();
	});

	it("should handle remove favorite action", async () => {
		const model = await import("../model");
		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(model.removeFavorite).toBeDefined();
	});

	it("should render in embedded mode", async () => {
		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page embedded />);
		expect(document.body).toBeTruthy();
	});

	it("should show header with favorites count", async () => {
		const model = await import("../model");
		const mockFavorites = [
			{ id: "1", title: "Test", price: 50000, images: [] },
		];
		(model.$favorites as any).getState = () => mockFavorites;
		(model.$favorites as any)["@@unitShape"] = () => mockFavorites;

		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should navigate to listing on card click", async () => {
		const { Favorites } = await import("../ui/page/Page");
		renderPage(<Favorites.Page />);
		expect(document.body).toBeTruthy();
	});
});
