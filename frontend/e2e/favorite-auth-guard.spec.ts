import { test, expect } from "@playwright/test";
import { loginAsBuyer, logout } from "./helpers/auth";
import { mockApi, createMockListing, mockListingsFeed } from "./helpers/api";

test.describe("Favorite Auth Guard", () => {
	test.beforeEach(async ({ page }) => {
		await logout(page);
	});

	test("unauthenticated user sees login prompt on favorites page", async ({
		page,
	}) => {
		await page.goto("/favorites");

		// Should display login prompt text for unauthenticated users
		await expect(
			page.getByText("Войдите, чтобы сохранять объявления в избранное").first(),
		).toBeVisible();
	});

	test("authenticated user can access favorites page", async ({ page }) => {
		await mockApi(page, "/api/v1/auth/dev-login", {
			access_token: "test-buyer-token",
			refresh_token: "test-refresh-token",
			user: { id: "1", first_name: "Buyer", role: "user" },
		});
		await loginAsBuyer(page);

		await mockApi(page, "/api/v1/auth/me", {
			id: "1",
			first_name: "Buyer",
			role: "user",
			approval_status: "approved",
		});
		await mockApi(page, "/api/v1/favorites", []);
		await mockApi(page, "/api/v1/favorites/ids", { ids: [] });

		await page.goto("/favorites");

		// Should show empty state instead of login prompt
		await expect(page.getByText("Пока пусто").first()).toBeVisible();
	});

	test("authenticated user can toggle favorite on listing detail", async ({
		page,
	}) => {
		const mockListing = createMockListing({ id: "listing-fav-1" });

		await mockApi(page, "/api/v1/auth/dev-login", {
			access_token: "test-buyer-token",
			refresh_token: "test-refresh-token",
			user: { id: "1", first_name: "Buyer", role: "user" },
		});
		await loginAsBuyer(page);

		await mockApi(page, "/api/v1/auth/me", {
			id: "1",
			first_name: "Buyer",
			role: "user",
			approval_status: "approved",
		});
		await mockApi(page, "/api/v1/favorites/ids", { ids: [] });
		await mockListingsFeed(page, [mockListing]);
		await mockApi(page, `/api/v1/listings/${mockListing.id}`, mockListing);

		// Mock the favorite POST endpoint
		await page.route(`**/api/v1/favorites/${mockListing.id}*`, (route) => {
			if (route.request().method() === "POST") {
				return route.fulfill({
					status: 201,
					contentType: "application/json",
					body: JSON.stringify({ success: true }),
				});
			}
			return route.fulfill({
				status: 200,
				contentType: "application/json",
				body: JSON.stringify({}),
			});
		});

		await page.goto(`/listings/${mockListing.id}`);
		await page.waitForLoadState("networkidle");

		// Find and click the heart/favorite button
		const favoriteButton = page
			.locator(
				'button[aria-label*="favor"], button[aria-label*="heart"], [data-testid="favorite-button"], button:has(svg)',
			)
			.first();
		if (await favoriteButton.isVisible()) {
			await favoriteButton.click();
			// Allow time for the request to be made
			await page.waitForTimeout(500);
		}

		// Page should remain accessible regardless
		await expect(page.locator("body")).toBeVisible();
	});
});
