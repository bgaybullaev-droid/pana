/**
 * Auth token storage utilities.
 * Separated from auth model to avoid circular dependencies with api/client.
 *
 * Admin and buyer/seller panels use different localStorage keys
 * so logging into one panel does not authenticate the other.
 */

const BUYER_TOKEN_KEY = 'auth_token';
const BUYER_REFRESH_TOKEN_KEY = 'auth_refresh_token';
const ADMIN_TOKEN_KEY = 'admin_auth_token';
const ADMIN_REFRESH_TOKEN_KEY = 'admin_refresh_token';

/** Check if current route is admin context */
export function isAdminContext(): boolean {
  return window.location.pathname.startsWith('/admin');
}

export function getTokenKeys(scope?: string): { tokenKey: string; refreshKey: string } {
  const isAdmin = scope === 'admin' || (!scope && isAdminContext());
  return {
    tokenKey: isAdmin ? ADMIN_TOKEN_KEY : BUYER_TOKEN_KEY,
    refreshKey: isAdmin ? ADMIN_REFRESH_TOKEN_KEY : BUYER_REFRESH_TOKEN_KEY,
  };
}

export function saveTokens(accessToken: string, refreshToken?: string, scope?: string) {
  const { tokenKey, refreshKey } = getTokenKeys(scope);
  localStorage.setItem(tokenKey, accessToken);
  if (refreshToken) {
    localStorage.setItem(refreshKey, refreshToken);
  }
}

export function getStoredToken(): string | null {
  const { tokenKey } = getTokenKeys();
  return localStorage.getItem(tokenKey);
}

export function getStoredRefreshToken(): string | null {
  const { refreshKey } = getTokenKeys();
  return localStorage.getItem(refreshKey);
}

export function clearStoredTokens() {
  const { tokenKey, refreshKey } = getTokenKeys();
  localStorage.removeItem(tokenKey);
  localStorage.removeItem(refreshKey);
}
