import { test, expect } from "@playwright/test";
import { logout } from "./helpers/auth";
import { mockApi, createMockListing } from "./helpers/api";

test.describe("Admin Listing Moderation", () => {
	test.beforeEach(async ({ page }) => {
		await logout(page);
	});

	test("admin can login and see dashboard", async ({ page }) => {
		// ``authResponseToUser`` (shared/state/auth/model/lib) reads the
		// user fields straight off the top-level response (not from a
		// nested ``user`` object), so the mock must expose
		// ``user_id``/``role``/``first_name`` directly — wrapping them
		// in ``{user: …}`` makes them all ``undefined`` and the role
		// check below silently fails.
		await mockApi(page, "/api/v1/auth/admin-login", {
			access_token: "admin-test-token",
			refresh_token: "admin-refresh-token",
			user_id: "admin-1",
			first_name: "Admin",
			role: "admin",
			approval_status: "approved",
		});
		// ``/auth/me`` is gated on the Authorization header: when the page
		// first loads (no token yet) the mock returns 401 so the
		// admin-login page renders its form. After the user submits and
		// the apiClient sets the bearer token, subsequent calls return
		// the admin profile and the page redirects to the dashboard.
		// Without this gate, the eager mock makes AuthProvider think the
		// user is already authenticated and the login form is skipped.
		await page.route("**/api/v1/auth/me*", (route) => {
			const auth = route.request().headers()["authorization"] || "";
			if (auth.toLowerCase().startsWith("bearer ")) {
				return route.fulfill({
					status: 200,
					contentType: "application/json",
					body: JSON.stringify({
						id: "admin-1",
						first_name: "Admin",
						role: "admin",
						approval_status: "approved",
					}),
				});
			}
			return route.fulfill({
				status: 401,
				contentType: "application/json",
				body: JSON.stringify({ detail: "Not authenticated" }),
			});
		});
		await mockApi(page, "/api/v1/admin/dashboard", {
			total_users: 150,
			pending_users: 8,
			approved_users: 130,
			rejected_users: 12,
			total_listings: 500,
			pending_listings: 15,
			approved_listings: 450,
			rejected_listings: 35,
		});

		await page.goto("/admin/login");
		await page.waitForLoadState("networkidle");

		// Fill the login form. Mantine's ``TextInput`` doesn't always
		// emit ``type="text"``, so widen the locator to any input that
		// isn't a password field (the form has exactly two inputs).
		const usernameInput = page
			.locator('input:not([type="password"])')
			.first();
		const passwordInput = page.locator('input[type="password"]').first();

		await expect(usernameInput).toBeVisible();
		await usernameInput.fill("test_admin");
		await passwordInput.fill("test_password");
		await page.locator('button[type="submit"]').click();

		// Wait for the redirect to land on the dashboard route. The
		// admin-login page's ``useEffect`` navigates to ``/admin`` once
		// ``$user.role === "admin"`` flips on, but the assertion below
		// can race that navigation if we only wait for ``networkidle``.
		await page.waitForURL(/\/admin(?!\/login)/, { timeout: 15000 });
		await page.waitForLoadState("networkidle");

		// Dashboard stats render — "150" appears as the total-users
		// count. Bump the visibility timeout so the first
		// fetch + render after navigation has room to settle.
		await expect(page.getByText("150").first()).toBeVisible({
			timeout: 15000,
		});
	});

	test("admin can view pending listings", async ({ context, page }) => {
		// Set admin token directly. ``addInitScript`` runs on the first
		// real navigation so we don't hit ``SecurityError`` calling
		// ``localStorage`` on the initial ``about:blank`` document.
		await context.addInitScript(() => {
			localStorage.setItem("admin_auth_token", "admin-test-token");
		});

		await mockApi(page, "/api/v1/auth/me", {
			id: "admin-1",
			first_name: "Admin",
			role: "admin",
			approval_status: "approved",
		});

		const pendingListing = createMockListing({
			moderation_status: "pending",
			title: "Pending Apartment Review",
		});
		await mockApi(page, "/api/v1/admin/listings", {
			items: [pendingListing],
			total: 1,
			page: 1,
			per_page: 20,
			total_pages: 1,
		});

		await page.goto("/admin/listings");
		await page.waitForLoadState("networkidle");

		// Listing cards should be visible
		await expect(
			page.getByText("Pending Apartment Review").first(),
		).toBeVisible();
	});

	test("non-admin redirected from admin panel", async ({ page }) => {
		// No admin token set — already cleared by logout in beforeEach

		await page.goto("/admin");
		await page.waitForLoadState("networkidle");

		// Should redirect to admin login page
		await expect(page).toHaveURL(/\/admin\/login/);

		// Login form elements should be visible
		await expect(page.locator('input[type="password"]').first()).toBeVisible();
	});
});
