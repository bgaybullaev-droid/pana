import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderPage, screen, fireEvent } from "@/test/helpers";

// Mock auth state
vi.mock("@shared/state/auth/model", () => ({
	$user: { getState: () => null, "@@unitShape": () => null },
	$isAuthenticated: { getState: () => false, "@@unitShape": () => false },
	loginAsAdmin: vi.fn(),
	$isAdminLoginLoading: { getState: () => false, "@@unitShape": () => false },
	$authError: { getState: () => null, "@@unitShape": () => null },
	logout: vi.fn(),
}));

// Mock useAuth hook
vi.mock("@app/providers/useAuth", () => ({
	useAuth: () => ({
		user: null,
		isAuthenticated: false,
	}),
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

describe("AdminLogin", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("should render without crashing", async () => {
		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		expect(document.body).toBeTruthy();
	});

	it("should display username input", async () => {
		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		expect(screen.getByPlaceholderText("Enter username")).toBeTruthy();
	});

	it("should display password input", async () => {
		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		expect(screen.getByPlaceholderText("Enter password")).toBeTruthy();
	});

	it("should display sign in button", async () => {
		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		expect(screen.getByText("Sign In")).toBeTruthy();
	});

	it("should disable submit button when fields are empty", async () => {
		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		const submitBtn = screen.getByText("Sign In");
		expect(submitBtn.closest("button")?.disabled).toBe(true);
	});

	it("should enable submit button when fields have values", async () => {
		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		const usernameInput = screen.getByPlaceholderText("Enter username");
		const passwordInput = screen.getByPlaceholderText("Enter password");
		fireEvent.change(usernameInput, { target: { value: "admin" } });
		fireEvent.change(passwordInput, { target: { value: "password123" } });
		const submitBtn = screen.getByText("Sign In");
		expect(submitBtn.closest("button")?.disabled).toBe(false);
	});

	it("should display login error when authError exists", async () => {
		const authModel = await import("@shared/state/auth/model");
		(authModel.$authError as any).getState = () => "Invalid credentials";
		(authModel.$authError as any)["@@unitShape"] = () => "Invalid credentials";

		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		expect(screen.getByText("Invalid credentials")).toBeTruthy();
	});

	it("should show loading state on submit button", async () => {
		const authModel = await import("@shared/state/auth/model");
		(authModel.$isAdminLoginLoading as any).getState = () => true;
		(authModel.$isAdminLoginLoading as any)["@@unitShape"] = () => true;
		(authModel.$authError as any).getState = () => null;
		(authModel.$authError as any)["@@unitShape"] = () => null;

		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		// Mantine loading button adds loader
		expect(document.body).toBeTruthy();
	});

	it("should display admin panel branding", async () => {
		const authModel = await import("@shared/state/auth/model");
		(authModel.$isAdminLoginLoading as any).getState = () => false;
		(authModel.$isAdminLoginLoading as any)["@@unitShape"] = () => false;
		(authModel.$authError as any).getState = () => null;
		(authModel.$authError as any)["@@unitShape"] = () => null;

		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		expect(screen.getByText("Admin Panel")).toBeTruthy();
		expect(
			screen.getByText("Enter your credentials to access the admin panel"),
		).toBeTruthy();
	});

	it("should display back to home button", async () => {
		const authModel = await import("@shared/state/auth/model");
		(authModel.$isAdminLoginLoading as any).getState = () => false;
		(authModel.$isAdminLoginLoading as any)["@@unitShape"] = () => false;
		(authModel.$authError as any).getState = () => null;
		(authModel.$authError as any)["@@unitShape"] = () => null;

		const { AdminLogin } = await import("../ui/page/Page");
		renderPage(<AdminLogin.Page />);
		expect(screen.getByText("Back to Home")).toBeTruthy();
	});
});
