import { createEvent } from 'effector';
import type { AuthUser } from '../types';

// Telegram Auth
export const authenticateWithTelegram = createEvent<string>();
export const logout = createEvent();
export const setUser = createEvent<AuthUser | null>();

// Seller Auth (legacy — kept for backward compat)
export const loginWithOLXPhone = createEvent<string>();
export const loginWithTelegramChannel = createEvent<string>();

// Seller OTP Auth
export const requestSellerOTP = createEvent<string>();
export const verifySellerOTP = createEvent<{ phone: string; otp_code: string }>();
export const resetSellerOTPStep = createEvent();

// Buyer Auth
export const loginWithBuyerPhone = createEvent<{ phone: string; first_name: string; last_name?: string }>();

// Admin Auth
export const loginAsAdmin = createEvent<{ username: string; password: string }>();

// Auth Check Complete Event
export const authCheckComplete = createEvent();

// Session Check
export const checkSession = createEvent();

// Dev Mode
export const devLogin = createEvent();
