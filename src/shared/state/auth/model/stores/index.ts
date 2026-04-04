import { createStore } from "effector";
import type { AuthUser } from "../types";

// User Store
export const $user = createStore<AuthUser | null>(null);

export const $isAuthenticated = $user.map(
	(user) => user !== null && !!user.phone,
);

// Track if user has logged out (to prevent auto re-login in dev mode)
export const $hasLoggedOut = createStore(false);

export const $isLoading = createStore(true);

// Auth Error Store
export const $authError = createStore<string | null>(null);

// Seller login loading (separate from main isLoading)
export const $isSellerLoginLoading = createStore(false);

// Buyer login loading
export const $isBuyerLoginLoading = createStore(false);

// Admin login loading
export const $isAdminLoginLoading = createStore(false);

// Seller OTP stores
export const $sellerOTPStep = createStore<"phone" | "otp">("phone");

export const $sellerOTPPhone = createStore<string | null>(null);

export const $isSellerOTPLoading = createStore(false);

export const $sellerOTPDevCode = createStore<string | null>(null);
