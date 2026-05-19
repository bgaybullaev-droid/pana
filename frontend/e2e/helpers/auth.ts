import { Page } from '@playwright/test';

const API_URL = '/api/v1';

// Canonical SPA token keys — must match ``frontend/src/shared/lib/auth-tokens.ts``.
// Drifting from these is how every "the test is logged in but the
// page renders as guest" bug starts.
const BUYER_TOKEN_KEY = 'auth_token';
const BUYER_REFRESH_KEY = 'auth_refresh_token';
const ADMIN_TOKEN_KEY = 'admin_auth_token';
const ADMIN_REFRESH_KEY = 'admin_refresh_token';

/**
 * Seed a value into ``localStorage`` so it's present on every navigation,
 * including the very first ``page.goto()``. Calling ``page.evaluate``
 * with ``localStorage`` on the initial ``about:blank`` document raises
 * ``SecurityError: Access is denied`` — ``addInitScript`` runs at
 * document-init time and isn't subject to that restriction.
 *
 * If the test has already navigated to a real origin, we also write
 * the value into the current page so the seed takes effect without
 * requiring a fresh navigation.
 *
 * When seeding a real auth token, also clear ``dev_logged_out`` so the
 * AuthProvider's dev-mode auto-login short-circuit doesn't fire on
 * top of our seed and immediately wipe the session.
 */
async function _seedLocalStorage(
  page: Page,
  key: string,
  value: string,
): Promise<void> {
  const isAuthKey =
    key === BUYER_TOKEN_KEY || key === ADMIN_TOKEN_KEY;
  await page.context().addInitScript(
    ([k, v, clearDevFlag]) => {
      try {
        localStorage.setItem(k as string, v as string);
        if (clearDevFlag) {
          localStorage.removeItem('dev_logged_out');
        }
      } catch {
        /* ignore: opaque origin (about:blank) */
      }
    },
    [key, value, isAuthKey],
  );
  if (page.url().startsWith('http')) {
    await page.evaluate(
      ([k, v, clearDevFlag]) => {
        localStorage.setItem(k as string, v as string);
        if (clearDevFlag) {
          localStorage.removeItem('dev_logged_out');
        }
      },
      [key, value, isAuthKey],
    );
  }
}

/**
 * Login as a buyer.
 *
 * ``page.request.post`` makes a Node-side network call that **bypasses**
 * ``page.route()`` mocks (those only intercept browser-context fetches).
 * Hitting the real backend during a unit-style e2e test yields empty/
 * unexpected responses that the original helper tried to ``.json()`` and
 * crashed on ``Unexpected end of JSON input``.
 *
 * The tests that call this helper always mock ``/api/v1/auth/me``
 * separately, so the SPA's actual auth path is driven by that mock —
 * all this helper needs to do is seed an auth token value at the key
 * the SPA actually reads (``auth_token``), so the API client attaches
 * an ``Authorization: Bearer …`` header on subsequent calls.
 */
export async function loginAsBuyer(page: Page): Promise<void> {
  void API_URL; // kept for callers that may still want the real flow later
  await _seedLocalStorage(page, BUYER_TOKEN_KEY, 'e2e-test-buyer-token');
}

/**
 * Login as admin. Seeds the canonical ``admin_auth_token`` key — the
 * SPA's apiClient looks here when the route is ``/admin/...``.
 * See ``loginAsBuyer`` for the rationale on skipping the network
 * round-trip.
 */
export async function loginAsAdmin(
  page: Page,
  _username: string,
  _password: string,
): Promise<void> {
  await _seedLocalStorage(page, ADMIN_TOKEN_KEY, 'e2e-test-admin-token');
}

/**
 * Login as seller. Sellers use the same ``auth_token`` key as buyers
 * (the role distinction lives in the ``/auth/me`` response, not in
 * the token-key namespace).
 */
export async function loginAsSeller(page: Page, _phone: string): Promise<void> {
  await _seedLocalStorage(page, BUYER_TOKEN_KEY, 'e2e-test-seller-token');
}

/**
 * Clear all auth tokens — both the canonical SPA keys and the legacy
 * ``access_token`` / ``admin_access_token`` names a few older tests
 * still write. Uses ``addInitScript`` so the clear takes effect on
 * every subsequent ``page.goto()`` even if the page hasn't been
 * navigated yet (the original ``page.evaluate`` approach raises
 * ``SecurityError`` on the initial ``about:blank`` document).
 *
 * Also sets ``dev_logged_out=true`` — without this flag the
 * ``AuthProvider`` will silently auto-``devLogin()`` on first render
 * (``isDev && !hasDevLoggedOut`` branch in
 * ``src/app/providers/AuthProvider.tsx``), which masks logged-out
 * UI states and prevents login forms from rendering.
 */
export async function logout(page: Page): Promise<void> {
  const keys = [
    BUYER_TOKEN_KEY,
    BUYER_REFRESH_KEY,
    ADMIN_TOKEN_KEY,
    ADMIN_REFRESH_KEY,
    // Legacy names kept for older callers / migrated test data
    'access_token',
    'refresh_token',
    'admin_access_token',
  ];
  await page.context().addInitScript((tokens) => {
    try {
      for (const k of tokens) localStorage.removeItem(k);
      localStorage.setItem('dev_logged_out', 'true');
    } catch {
      /* ignore opaque-origin failures */
    }
  }, keys);
  if (page.url().startsWith('http')) {
    await page.evaluate((tokens) => {
      for (const k of tokens) localStorage.removeItem(k);
      localStorage.setItem('dev_logged_out', 'true');
    }, keys);
  }
}

/**
 * Check if user is authenticated. Requires the page to have already
 * navigated to a real origin; returns ``false`` on ``about:blank``.
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  if (!page.url().startsWith('http')) {
    return false;
  }
  return page.evaluate(
    (key) => !!localStorage.getItem(key),
    BUYER_TOKEN_KEY,
  );
}
