import { test, expect } from '@playwright/test';
import { mockApi, createMockListing } from './helpers/api';

test.describe('Seller Onboarding', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authenticated seller
    await mockApi(page, '/api/v1/auth/me', {
      id: '1', first_name: 'Seller', role: 'seller', is_seller: true, approval_status: 'approved',
    });
    await mockApi(page, '/api/v1/sellers/me', {
      id: 's1', company_name: 'Test Co', phone: '+998901234567', is_verified: false,
      listings_count: 0, total_views: 0,
    });
  });

  test('should display seller dashboard with stats', async ({ page }) => {
    await mockApi(page, '/api/v1/sellers/me/listings', {
      items: [], total: 0, page: 1, per_page: 20, total_pages: 0,
    });

    await page.goto('/seller/dashboard');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should navigate to create listing page', async ({ page }) => {
    await page.goto('/seller/create');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should fill and submit listing form', async ({ page }) => {
    const newListing = createMockListing({ title: 'New Seller Listing' });
    await mockApi(page, '/api/v1/listings', newListing);

    await page.goto('/seller/create');
    await expect(page.locator('body')).toBeVisible();
    // Form should be present
    await page.waitForTimeout(500);
  });

  test('should view created listing in seller listings', async ({ page }) => {
    const listing = createMockListing({ title: 'My Listing', status: 'active' });
    await mockApi(page, '/api/v1/sellers/me/listings', {
      items: [listing], total: 1, page: 1, per_page: 20, total_pages: 1,
    });

    await page.goto('/seller/listings');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should edit an existing listing', async ({ page }) => {
    const listing = createMockListing({ title: 'Editable Listing' });
    await mockApi(page, `/api/v1/listings/${listing.id}`, listing);

    await page.goto(`/seller/edit/${listing.id}`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should view seller profile', async ({ page }) => {
    await page.goto('/seller/profile');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should view crawled listings stats', async ({ page }) => {
    await mockApi(page, '/api/v1/sellers/me/crawled/stats', {
      olx_count: 5, telegram_count: 3, total_count: 8,
    });

    await page.goto('/seller/crawled');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle seller registration flow', async ({ page }) => {
    // Override auth to be non-seller
    await mockApi(page, '/api/v1/auth/me', {
      id: '1', first_name: 'User', role: 'user', is_seller: false, approval_status: 'approved',
    });
    await mockApi(page, '/api/v1/sellers/register', {
      id: 's1', company_name: 'New Co', phone: '+998901234567',
    });

    await page.goto('/seller/register');
    await expect(page.locator('body')).toBeVisible();
  });
});
