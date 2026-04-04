import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios';
import { isAdminContext } from '@shared/lib/auth-tokens';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

// Serialize arrays as repeated params (rooms=1&rooms=2) for FastAPI compatibility
const paramsSerializer = (params: Record<string, unknown>): string => {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      for (const item of value) {
        parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(item))}`);
      }
    } else {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
    }
  }
  return parts.join('&');
};

// Create axios instance
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  paramsSerializer,
});

// =============================================================================
// Proactive Token Refresh
// =============================================================================

/** Decode JWT payload without verification (just base64) */
function decodeJwtPayload(token: string): { exp?: number } | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
    return payload;
  } catch {
    return null;
  }
}

/** Returns seconds until the access token expires, or -1 if unknown */
function getTokenTTL(): number {
  const tokenKey = isAdminContext() ? 'admin_auth_token' : 'auth_token';
  const token = localStorage.getItem(tokenKey);
  if (!token) return -1;
  const payload = decodeJwtPayload(token);
  if (!payload?.exp) return -1;
  return payload.exp - Math.floor(Date.now() / 1000);
}

// Refresh the access token proactively 2 minutes before it expires.
// The timer is (re)started after every successful token save.
let proactiveRefreshTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleProactiveRefresh() {
  if (proactiveRefreshTimer) {
    clearTimeout(proactiveRefreshTimer);
    proactiveRefreshTimer = null;
  }
  const ttl = getTokenTTL();
  if (ttl <= 0) return; // no token or already expired

  // Refresh 2 minutes before expiry (minimum 10 seconds)
  const refreshIn = Math.max(ttl - 120, 10) * 1000;

  proactiveRefreshTimer = setTimeout(async () => {
    proactiveRefreshTimer = null;
    try {
      await runTokenRefresh();
    } catch {
      // Proactive refresh failed — the 401 interceptor will handle it reactively
    }
  }, refreshIn);
}

// =============================================================================
// Token Refresh Mutex
// =============================================================================

// Ensures only one refresh request runs at a time.
// Concurrent 401 responses wait for the same promise.
let refreshPromise: Promise<void> | null = null;

async function runTokenRefresh(): Promise<void> {
  // If a refresh is already in progress, piggy-back on it
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const isAdmin = isAdminContext();
    const refreshTokenKey = isAdmin ? 'admin_refresh_token' : 'auth_refresh_token';
    const accessTokenKey = isAdmin ? 'admin_auth_token' : 'auth_token';

    const refreshToken = localStorage.getItem(refreshTokenKey);
    const refreshResponse = await apiClient.post('/auth/refresh',
      refreshToken ? { refresh_token: refreshToken } : undefined
    );

    // Save new tokens
    if (refreshResponse.data?.access_token) {
      localStorage.setItem(accessTokenKey, refreshResponse.data.access_token);
      if (refreshResponse.data?.refresh_token) {
        localStorage.setItem(refreshTokenKey, refreshResponse.data.refresh_token);
      }
      // Re-schedule proactive refresh with the new token's TTL
      scheduleProactiveRefresh();
    }
  })();

  try {
    await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

// =============================================================================
// Request Interceptor
// =============================================================================

// Adds Authorization header from localStorage as fallback.
// Uses separate token keys for admin vs buyer/seller contexts.
apiClient.interceptors.request.use(
  (config) => {
    // Primary auth is via httpOnly cookies (withCredentials: true)
    // Fallback: use localStorage token as Authorization header
    const tokenKey = isAdminContext() ? 'admin_auth_token' : 'auth_token';
    const token = localStorage.getItem(tokenKey);
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Send content language preference for multilingual listing resolution
    const lang = localStorage.getItem('i18nextLng') || 'ru';
    config.headers['Accept-Language'] = lang;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// =============================================================================
// Response Interceptor
// =============================================================================

// Strip absolute backend URLs from responses so images load via the Vite proxy
// (e.g. "http://localhost:8001/uploads/..." → "/uploads/...")
function normalizeUrls(data: unknown): unknown {
  if (typeof data === 'string') {
    return data.replace(/https?:\/\/[^/]+\/(uploads\/)/g, '/$1');
  }
  if (Array.isArray(data)) {
    return data.map(normalizeUrls);
  }
  if (data && typeof data === 'object') {
    const out: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data)) {
      out[key] = normalizeUrls(value);
    }
    return out;
  }
  return data;
}

apiClient.interceptors.response.use(
  (response) => {
    response.data = normalizeUrls(response.data);
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Skip refresh only for auth mutation endpoints (prevents infinite loops).
    // /auth/me is NOT skipped — it's a session check that should trigger refresh.
    const url = originalRequest.url || '';
    const isAuthMutation = url.includes('/auth/refresh') ||
      url.includes('/auth/logout') ||
      url.includes('/auth/telegram') ||
      url.includes('/auth/seller-otp') ||
      url.includes('/auth/buyer-phone') ||
      url.includes('/auth/admin-login') ||
      url.includes('/auth/dev-login');

    // Handle 401 - try to refresh token
    // Skip refresh if user has logged out in dev mode
    const hasDevLoggedOut = localStorage.getItem('dev_logged_out') === 'true';
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !hasDevLoggedOut &&
      !isAuthMutation
    ) {
      originalRequest._retry = true;

      try {
        await runTokenRefresh();
        // Retry the original request with the new token
        return apiClient(originalRequest);
      } catch {
        // Token refresh failed - clear localStorage tokens for current context
        const isAdmin = isAdminContext();
        localStorage.removeItem(isAdmin ? 'admin_auth_token' : 'auth_token');
        localStorage.removeItem(isAdmin ? 'admin_refresh_token' : 'auth_refresh_token');
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);

// =============================================================================
// Exports
// =============================================================================

/** Call after successful login to start the proactive refresh timer */
export function startTokenRefreshTimer() {
  scheduleProactiveRefresh();
}

/** Call on logout to clear the proactive refresh timer */
export function stopTokenRefreshTimer() {
  if (proactiveRefreshTimer) {
    clearTimeout(proactiveRefreshTimer);
    proactiveRefreshTimer = null;
  }
}

// API error type
export interface ApiError {
  code: string;
  message: string;
  details?: Array<{
    field: string;
    error: string;
  }>;
}

// Extract error from response
export function getApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error) && error.response?.data?.error) {
    return error.response.data.error;
  }
  return {
    code: 'UNKNOWN_ERROR',
    message: 'An unexpected error occurred',
  };
}
