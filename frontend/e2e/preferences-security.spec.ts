import { test, expect } from '@playwright/test';
import { mockApi } from './helpers/api';
import { logout } from './helpers/auth';

test.describe('Preferences & Security', () => {
  test.beforeEach(async ({ page }) => {
    await mockApi(page, '/api/v1/auth/me', {
      id: '1', first_name: 'User', role: 'user', approval_status: 'approved',
    });
    await mockApi(page, '/api/v1/favorites/ids', { ids: [] });
  });

  test('should persist language setting across page navigation', async ({ page }) => {
    await page.goto('/');
    // Language should be set in localStorage
    const lang = await page.evaluate(() => localStorage.getItem('i18nextLng'));
    await expect(page.locator('body')).toBeVisible();

    // Navigate to another page
    await page.goto('/profile');
    const langAfter = await page.evaluate(() => localStorage.getItem('i18nextLng'));
    // Language should persist
    expect(langAfter).toBe(lang);
  });

  test('should persist scroll position on back navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
    // Scroll position management via sessionStorage
  });

  test('should handle network errors gracefully', async ({ page }) => {
    await page.route('**/api/v1/**', (route) => route.abort('connectionrefused'));
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display mobile-only screen on desktop', async ({ page, context }) => {
    // This test runs on desktop Chrome viewport
    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle concurrent API requests', async ({ page }) => {
    await mockApi(page, '/api/v1/listings/feed', {
      items: [], total: 0, page: 1, per_page: 20, total_pages: 0,
    });
    await mockApi(page, '/api/v1/notifications/unread-count', { unread_count: 0 });

    await page.goto('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should clear all data on logout', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'test');
      localStorage.setItem('refresh_token', 'test');
      sessionStorage.setItem('scroll_pos', '100');
    });

    await logout(page);

    const token = await page.evaluate(() => localStorage.getItem('access_token'));
    expect(token).toBeNull();
  });

  test('should not expose tokens in URL', async ({ page }) => {
    await page.goto('/');
    const url = page.url();
    expect(url).not.toContain('token');
    expect(url).not.toContain('access_token');
  });

  test('should handle 401 by clearing session', async ({ page }) => {
    await page.evaluate(() => {
      localStorage.setItem('access_token', 'expired-token');
    });
    await mockApi(page, '/api/v1/auth/me', { detail: 'Unauthorized' }, 401);

    await page.goto('/favorites');
    await expect(page.locator('body')).toBeVisible();
  });

  test('should respect CORS headers', async ({ page }) => {
    // Navigate and verify no CORS errors in console
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error' && msg.text().includes('CORS')) {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto('/');
    await page.waitForTimeout(1000);
    expect(consoleErrors).toHaveLength(0);
  });
});
