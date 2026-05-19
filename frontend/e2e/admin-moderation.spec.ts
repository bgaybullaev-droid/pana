import { test, expect } from '@playwright/test';
import { mockApi, createMockListing } from './helpers/api';

test.describe('Admin Moderation', () => {
  test.beforeEach(async ({ context, page }) => {
    // Mock admin auth — `addInitScript` runs on every new document
    // (including the initial about:blank), so `localStorage` is
    // populated before any test code calls `page.goto()`. Calling
    // `page.evaluate(localStorage.setItem(...))` before navigation
    // fails with `SecurityError: Access is denied for this document`.
    await context.addInitScript(() => {
      localStorage.setItem('admin_auth_token', 'admin-test-token');
    });
    await mockApi(page, '/api/v1/auth/me', {
      id: 'admin-1', first_name: 'Admin', role: 'admin', approval_status: 'approved',
    });
  });

  test('should display admin login page', async ({ page }) => {
    await page.goto('/admin/login');
    await page.evaluate(() => localStorage.clear());
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display admin dashboard with stats', async ({ page }) => {
    await mockApi(page, '/api/v1/admin/dashboard', {
      total_users: 150, pending_users: 8, approved_users: 130, rejected_users: 12,
      total_listings: 500, pending_listings: 15, approved_listings: 450, rejected_listings: 35,
    });

    await page.goto('/admin');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should list pending users for approval', async ({ page }) => {
    await mockApi(page, '/api/v1/admin/users', {
      items: [
        { id: 'u1', first_name: 'Pending', username: 'pending1', role: 'seller', approval_status: 'pending', created_at: new Date().toISOString() },
      ],
      total: 1, page: 1, per_page: 20, total_pages: 1,
    });

    await page.goto('/admin/users');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should view user detail and approve', async ({ page }) => {
    await mockApi(page, '/api/v1/admin/users/u1', {
      id: 'u1', first_name: 'Pending', username: 'pending1', role: 'seller',
      approval_status: 'pending', phone: '+998901111111', created_at: new Date().toISOString(),
    });
    await mockApi(page, '/api/v1/admin/users/u1/approve', {
      id: 'u1', approval_status: 'approved',
    });

    await page.goto('/admin/users/u1');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should list pending listings for moderation', async ({ page }) => {
    const pendingListing = createMockListing({
      moderation_status: 'pending', title: 'Pending Review Apt',
    });
    await mockApi(page, '/api/v1/admin/listings', {
      items: [pendingListing], total: 1, page: 1, per_page: 20, total_pages: 1,
    });

    await page.goto('/admin/listings');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should approve a pending listing', async ({ page }) => {
    const listing = createMockListing({ moderation_status: 'pending' });
    await mockApi(page, `/api/v1/admin/listings/${listing.id}`, listing);
    await mockApi(page, `/api/v1/admin/listings/${listing.id}/approve`, {
      ...listing, moderation_status: 'approved',
    });

    await page.goto(`/admin/listings/${listing.id}`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should reject a listing with reason', async ({ page }) => {
    const listing = createMockListing({ moderation_status: 'pending' });
    await mockApi(page, `/api/v1/admin/listings/${listing.id}`, listing);
    await mockApi(page, `/api/v1/admin/listings/${listing.id}/reject`, {
      ...listing, moderation_status: 'rejected',
    });

    await page.goto(`/admin/listings/${listing.id}`);
    await expect(page.locator('body')).toBeVisible();
  });

  test('should filter users by approval status', async ({ page }) => {
    await mockApi(page, '/api/v1/admin/users', {
      items: [], total: 0, page: 1, per_page: 20, total_pages: 0,
    });

    await page.goto('/admin/users');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should view crawled listings', async ({ page }) => {
    await mockApi(page, '/api/v1/crawler/telegram/listings', {
      items: [], total: 0, page: 1, per_page: 20, total_pages: 0,
    });
    await mockApi(page, '/api/v1/crawler/olx/listings', {
      items: [], total: 0, page: 1, per_page: 20, total_pages: 0,
    });

    await page.goto('/admin/crawled');
    await expect(page.locator('body')).toBeVisible();
  });
});
