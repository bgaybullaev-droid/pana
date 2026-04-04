import { Page } from '@playwright/test';

const API_URL = '/api/v1';

/**
 * Login as a buyer via the dev-login endpoint.
 * Sets the access token in localStorage for subsequent requests.
 */
export async function loginAsBuyer(page: Page): Promise<void> {
  const response = await page.request.post(`${API_URL}/auth/dev-login`);
  const data = await response.json();

  await page.evaluate((token: string) => {
    localStorage.setItem('access_token', token);
  }, data.access_token);
}

/**
 * Login as admin via admin-login endpoint.
 */
export async function loginAsAdmin(page: Page, username: string, password: string): Promise<void> {
  const response = await page.request.post(`${API_URL}/auth/admin-login`, {
    data: { username, password },
  });
  const data = await response.json();

  await page.evaluate((token: string) => {
    localStorage.setItem('admin_access_token', token);
  }, data.access_token);
}

/**
 * Login as seller via buyer-phone endpoint (simplified for E2E).
 */
export async function loginAsSeller(page: Page, phone: string): Promise<void> {
  const response = await page.request.post(`${API_URL}/auth/buyer-phone`, {
    data: { phone, first_name: 'E2E Seller' },
  });
  const data = await response.json();

  await page.evaluate((token: string) => {
    localStorage.setItem('access_token', token);
  }, data.access_token);
}

/**
 * Clear all auth tokens.
 */
export async function logout(page: Page): Promise<void> {
  await page.evaluate(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('admin_access_token');
  });
}

/**
 * Check if user is authenticated.
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  return page.evaluate(() => !!localStorage.getItem('access_token'));
}
