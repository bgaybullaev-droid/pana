import { sample } from "effector";
import { getApiError } from "@shared/api/client";
import { authResponseToUser, userMeResponseToUser } from "../lib";
import {
	authenticateWithTelegram,
	logout,
	setUser,
	loginWithOLXPhone,
	loginWithTelegramChannel,
	requestSellerOTP,
	verifySellerOTP,
	resetSellerOTPStep,
	loginWithBuyerPhone,
	loginAsAdmin,
	authCheckComplete,
	checkSession,
	devLogin,
} from "../events";
import {
	authenticateWithTelegramFx,
	checkSessionFx,
	logoutFx,
	loginWithOLXPhoneFx,
	loginWithTelegramChannelFx,
	loginWithBuyerPhoneFx,
	loginAsAdminFx,
	requestSellerOTPFx,
	verifySellerOTPFx,
	devLoginFx,
	updateProfileFx,
	updateLanguageFx,
} from "../effects";
import {
	$user,
	$hasLoggedOut,
	$isLoading,
	$authError,
	$isSellerLoginLoading,
	$isBuyerLoginLoading,
	$isAdminLoginLoading,
	$sellerOTPStep,
	$sellerOTPPhone,
	$isSellerOTPLoading,
	$sellerOTPDevCode,
	$sellerOTPExpiresAt,
} from "../stores";

// =============================================================================
// $user wiring
// =============================================================================

$user
	.on(checkSessionFx.doneData, (_, data) => userMeResponseToUser(data))
	.on(authenticateWithTelegramFx.doneData, (_, data) =>
		authResponseToUser(data),
	)
	.on(loginWithOLXPhoneFx.doneData, (_, data) => authResponseToUser(data))
	.on(loginWithTelegramChannelFx.doneData, (_, data) =>
		authResponseToUser(data),
	)
	.on(loginWithBuyerPhoneFx.doneData, (_, data) => authResponseToUser(data))
	.on(loginAsAdminFx.doneData, (_, data) => authResponseToUser(data, "admin"))
	.on(verifySellerOTPFx.doneData, (_, data) =>
		authResponseToUser(data, "seller"),
	)
	.on(setUser, (_, user) => user)
	.on(updateProfileFx.doneData, (_, data) => userMeResponseToUser(data))
	.on(updateLanguageFx.doneData, (_, data) => userMeResponseToUser(data))
	// Reset on the event (instant UI update) AND on effect completion (belt
	// and braces, in case something triggers logoutFx without the event).
	.reset(logout)
	.reset(logoutFx.done);

// =============================================================================
// $hasLoggedOut wiring
// =============================================================================

$hasLoggedOut
	.on(logout, () => true)
	.on(logoutFx.done, () => true)
	.reset(checkSessionFx.done)
	.reset(authenticateWithTelegramFx.done)
	.reset(loginWithOLXPhoneFx.done)
	.reset(loginWithTelegramChannelFx.done)
	.reset(loginWithBuyerPhoneFx.done)
	.reset(loginAsAdminFx.done)
	.reset(verifySellerOTPFx.done);

// =============================================================================
// $isLoading wiring
// =============================================================================

$isLoading
	.on(checkSessionFx.done, () => false)
	// checkSessionFx.fail intentionally NOT handled — fallback auth will set loading to false
	.on(authenticateWithTelegramFx.pending, (_, pending) => pending)
	.on(authenticateWithTelegramFx.finally, () => false)
	// Handle buyer/seller phone login loading states
	.on(loginWithBuyerPhoneFx.pending, (_, pending) => pending)
	.on(loginWithBuyerPhoneFx.finally, () => false)
	.on(loginWithOLXPhoneFx.pending, (_, pending) => pending)
	.on(loginWithOLXPhoneFx.finally, () => false)
	.on(loginWithTelegramChannelFx.pending, (_, pending) => pending)
	.on(loginWithTelegramChannelFx.finally, () => false)
	// Handle admin login loading state
	.on(loginAsAdminFx.pending, (_, pending) => pending)
	.on(loginAsAdminFx.finally, () => false)
	// Handle seller OTP verify loading state
	.on(verifySellerOTPFx.pending, (_, pending) => pending)
	.on(verifySellerOTPFx.finally, () => false);

$isLoading.on(authCheckComplete, () => false);

// =============================================================================
// $authError wiring
// =============================================================================

$authError
	.on(
		authenticateWithTelegramFx.failData,
		(_, error) => getApiError(error).message,
	)
	.on(loginWithOLXPhoneFx.failData, (_, error) => getApiError(error).message)
	.on(
		loginWithTelegramChannelFx.failData,
		(_, error) => getApiError(error).message,
	)
	.on(loginWithBuyerPhoneFx.failData, (_, error) => getApiError(error).message)
	.on(loginAsAdminFx.failData, (_, error) => getApiError(error).message)
	.on(requestSellerOTPFx.failData, (_, error) => getApiError(error).message)
	.on(verifySellerOTPFx.failData, (_, error) => getApiError(error).message)
	.reset(authenticateWithTelegram)
	.reset(loginWithOLXPhone)
	.reset(loginWithTelegramChannel)
	.reset(loginWithBuyerPhone)
	.reset(loginAsAdmin)
	.reset(requestSellerOTP)
	.reset(verifySellerOTP)
	.reset(logout);

// =============================================================================
// $isSellerLoginLoading wiring
// =============================================================================

$isSellerLoginLoading
	.on(loginWithOLXPhoneFx.pending, (_, p) => p)
	.on(loginWithTelegramChannelFx.pending, (_, p) => p);

// =============================================================================
// $isBuyerLoginLoading wiring
// =============================================================================

$isBuyerLoginLoading.on(loginWithBuyerPhoneFx.pending, (_, p) => p);

// =============================================================================
// $isAdminLoginLoading wiring
// =============================================================================

$isAdminLoginLoading.on(loginAsAdminFx.pending, (_, p) => p);

// =============================================================================
// $sellerOTPStep wiring
// =============================================================================

$sellerOTPStep
	.on(requestSellerOTPFx.doneData, () => "otp")
	.on(resetSellerOTPStep, () => "phone")
	.reset(verifySellerOTPFx.done)
	.reset(logout)
	.reset(logoutFx.done);

// =============================================================================
// $sellerOTPPhone wiring
// =============================================================================

$sellerOTPPhone
	.on(requestSellerOTP, (_, phone) => phone)
	.on(resetSellerOTPStep, () => null)
	.reset(logout)
	.reset(logoutFx.done);

// =============================================================================
// $isSellerOTPLoading wiring
// =============================================================================

$isSellerOTPLoading
	.on(requestSellerOTPFx.pending, (_, p) => p)
	.on(verifySellerOTPFx.pending, (_, p) => p);

// =============================================================================
// $sellerOTPDevCode wiring
// =============================================================================

$sellerOTPDevCode
	.on(requestSellerOTPFx.doneData, (_, data) => data._dev_otp ?? null)
	.on(resetSellerOTPStep, () => null);

// =============================================================================
// $sellerOTPExpiresAt wiring
// =============================================================================

$sellerOTPExpiresAt
	.on(requestSellerOTPFx.doneData, (_, data) => {
		// Use standard 60 seconds if the backend doesn't provide it
		const expiresIn = data.expires_in ?? 60;
		return Date.now() + expiresIn * 1000;
	})
	.on(resetSellerOTPStep, () => null)
	.reset(verifySellerOTPFx.done);

// =============================================================================
// Sample Connections
// =============================================================================

sample({
	clock: authenticateWithTelegram,
	target: authenticateWithTelegramFx,
});

sample({
	clock: logout,
	target: logoutFx,
});

sample({
	clock: loginWithOLXPhone,
	target: loginWithOLXPhoneFx,
});

sample({
	clock: loginWithTelegramChannel,
	target: loginWithTelegramChannelFx,
});

sample({
	clock: loginWithBuyerPhone,
	target: loginWithBuyerPhoneFx,
});

sample({
	clock: loginAsAdmin,
	target: loginAsAdminFx,
});

sample({
	clock: requestSellerOTP,
	fn: (phone) => `+998${phone.replace(/\D/g, "").slice(-9)}`,
	target: requestSellerOTPFx,
});

sample({
	clock: verifySellerOTP,
	target: verifySellerOTPFx,
});

sample({
	clock: checkSession,
	target: checkSessionFx,
});

// =============================================================================
// Dev Mode wiring
// =============================================================================

$user.on(devLoginFx.doneData, (_, data) => authResponseToUser(data));
$isLoading.on(devLoginFx.pending, (_, pending) => pending);
$isLoading.on(devLoginFx.finally, () => false);
$hasLoggedOut.reset(devLoginFx.done);

sample({
	clock: devLogin,
	target: devLoginFx,
});
