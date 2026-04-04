import { sample } from "effector";
import { getApiError } from "@shared/api/client";
import {
	logoutFx,
	checkSessionFx,
	verifySellerOTPFx,
} from "@shared/state/auth/model";
import {
	fetchSellerProfile,
	registerAsSeller,
	updateSellerProfile,
	fetchSellerListings,
	pauseListing,
	activateListing,
	deleteListing,
	resetSellerState,
} from "../events";
import {
	fetchSellerProfileFx,
	registerAsSellerFx,
	updateSellerProfileFx,
	fetchSellerListingsFx,
	pauseListingFx,
	activateListingFx,
	deleteListingFx,
} from "../effects";
import {
	$sellerProfile,
	$sellerListings,
	$sellerListingsPagination,
	$profileCheckComplete,
	$isLoadingProfile,
	$isLoadingListings,
	$sellerError,
} from "../stores";

// --- Store wiring (.on / .reset) ---

$sellerProfile
	.on(fetchSellerProfileFx.doneData, (_, seller) => seller)
	.on(registerAsSellerFx.doneData, (_, seller) => seller)
	.on(updateSellerProfileFx.doneData, (_, seller) => seller)
	.reset(resetSellerState)
	.reset(logoutFx.done);

$sellerListings
	.on(fetchSellerListingsFx.doneData, (_, response) => response.items)
	.on(pauseListingFx.doneData, (state, listingId) =>
		state.map((listing) =>
			listing.id === listingId
				? { ...listing, status: "paused" as const }
				: listing,
		),
	)
	.on(activateListingFx.doneData, (state, listingId) =>
		state.map((listing) =>
			listing.id === listingId
				? { ...listing, status: "active" as const }
				: listing,
		),
	)
	.on(deleteListingFx.doneData, (state, listingId) =>
		state.filter((listing) => listing.id !== listingId),
	)
	.reset(resetSellerState)
	.reset(logoutFx.done);

$sellerListingsPagination
	.on(fetchSellerListingsFx.doneData, (_, response) => ({
		page: response.page,
		perPage: response.per_page,
		total: response.total,
		totalPages: response.total_pages,
	}))
	.reset(resetSellerState);

$profileCheckComplete
	.on(fetchSellerProfileFx.done, () => true)
	.on(fetchSellerProfileFx.fail, () => true)
	.on(registerAsSellerFx.done, () => true)
	.reset(resetSellerState)
	.reset(logoutFx.done)
	.reset(verifySellerOTPFx.done);

$isLoadingProfile
	.on(fetchSellerProfileFx.pending, (_, pending) => pending)
	.on(registerAsSellerFx.pending, (_, pending) => pending);

$isLoadingListings.on(fetchSellerListingsFx.pending, (_, pending) => pending);

$sellerError
	.on(fetchSellerProfileFx.failData, (_, error) => getApiError(error).message)
	.on(registerAsSellerFx.failData, (_, error) => getApiError(error).message)
	.on(updateSellerProfileFx.failData, (_, error) => getApiError(error).message)
	.reset(fetchSellerProfileFx)
	.reset(registerAsSellerFx)
	.reset(updateSellerProfileFx);

// --- Sample connections ---

sample({
	clock: fetchSellerProfile,
	target: fetchSellerProfileFx,
});

sample({
	clock: registerAsSeller,
	target: registerAsSellerFx,
});

// Re-fetch session after seller registration to update $user.is_seller
sample({
	clock: registerAsSellerFx.done,
	target: checkSessionFx,
});

sample({
	clock: updateSellerProfile,
	target: updateSellerProfileFx,
});

sample({
	clock: fetchSellerListings,
	target: fetchSellerListingsFx,
});

sample({
	clock: pauseListing,
	target: pauseListingFx,
});

sample({
	clock: activateListing,
	target: activateListingFx,
});

sample({
	clock: deleteListing,
	target: deleteListingFx,
});
