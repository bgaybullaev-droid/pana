import { Page, expect } from '@playwright/test';

/**
 * Wait for an API response matching the URL pattern.
 */
export async function waitForApi(page: Page, urlPattern: string | RegExp) {
  return page.waitForResponse(
    (resp) =>
      typeof urlPattern === 'string'
        ? resp.url().includes(urlPattern)
        : urlPattern.test(resp.url()),
  );
}

/**
 * Mock an API endpoint with a fixed response.
 */
export async function mockApi(
  page: Page,
  urlPattern: string,
  response: object,
  status = 200,
) {
  await page.route(`**${urlPattern}*`, (route) =>
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(response),
    }),
  );
}

/**
 * Mock the listings feed.
 */
export async function mockListingsFeed(page: Page, listings: object[] = []) {
  await mockApi(page, '/api/v1/listings/feed', {
    items: listings,
    total: listings.length,
    page: 1,
    per_page: 20,
    total_pages: 1,
  });
}

/**
 * Create a mock listing object.
 */
export function createMockListing(overrides: Record<string, any> = {}) {
  return {
    id: crypto.randomUUID(),
    title: 'Test Apartment in Tashkent',
    description: 'Beautiful 3-room apartment',
    price: 50000,
    currency: 'usd',
    type: 'sell',
    property_type: 'apartment',
    rooms: 3,
    area: 75,
    region: 'tashkent',
    district: 'yunusabad',
    status: 'active',
    moderation_status: 'approved',
    source: 'platform',
    images: [{ original_url: '/uploads/test.jpg', thumbnail_url: '/uploads/test_thumb.jpg' }],
    seller: { id: crypto.randomUUID(), company_name: 'Test Seller', phone: '+998901234567' },
    created_at: new Date().toISOString(),
    favorites_count: 0,
    views_count: 10,
    is_favorited: false,
    ...overrides,
  };
}
