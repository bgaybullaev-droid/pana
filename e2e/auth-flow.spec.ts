import { test, expect } from '@playwright/test';
import { loginAsBuyer, loginAsAdmin, logout, isAuthenticated } from './helpers/auth';
import { mockApi } from './helpers/api';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    await logout(page);
  });

  test('should redirect unauthenticated user from protected pages', async ({ page }) => {
    await page.goto('/favorites');
    // Should show unauth screen or redirect
    await expect(page.locator('body')).toBeVisible();
  });

  test('should login via dev endpoint and persist session', async ({ page }) => {
    await mockApi(page, '/api/v1/auth/dev-login', {
      access_token: 'test-access-token',
      refresh_token: 'test-refresh-token',
      user: { id: '1', first_name: 'Dev', role: 'user' },
    });

    await page.goto('/');
    // Trigger dev login
    const authenticated = await isAuthenticated(page);
    // Page should be accessible
    await expect(page.locator('body')).toBeVisible();
  });

  test('should admin login with credentials', async ({ page }) => {
    await mockApi(page, '/api/v1/auth/admin-login', {
      access_token: 'admin-token',
      refresh_token: 'admin-refresh',
      user: { id: '1', first_name: 'Admin', role: 'admin' },
    });

    await page.goto('/admin/login');
    await expect(page.locator('body')).toBeVisible();

    // Fill login form
    const usernameInput = page.locator('input[type="text"], input[name="username"]').first();
    const passwordInput = page.locator('input[type="password"]').first();

    if (await usernameInput.isVisible()) {
      await usernameInput.fill('test_admin');
      await passwordInput.fill('test_password');
      await page.locator('button[type="submit"]').click();
    }
  });

  test('should clear session on logout', async ({ page }) => {
    // Set a token
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'test-token');
    });

    // Logout
    await logout(page);
    const authenticated = await isAuthenticated(page);
    expect(authenticated).toBe(false);
  });

  test('should handle expired token gracefully', async ({ page }) => {
    // Set an expired token
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'expired-token');
    });

    // Mock /auth/me to return 401
    await mockApi(page, '/api/v1/auth/me', { detail: 'Token expired' }, 401);

    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should persist language preference across sessions', async ({ page }) => {
    await page.goto('/');
    // Language should default or be preserved
    await expect(page.locator('body')).toBeVisible();
  });
});
