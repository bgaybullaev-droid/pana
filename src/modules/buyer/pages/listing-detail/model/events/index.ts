import { createEvent } from "effector";
import { seedListingIds } from "@modules/buyer/shared/state/model";

export const pageOpened = createEvent<string>(); // Initial listing ID
export { seedListingIds }; // Re-export from shared state
export const loadMore = createEvent();
export const toggleFavorite = createEvent<string>();
export const commentAdded = createEvent<string>(); // Listing ID where comment was added

// Fired by the slider whenever the visible slide changes (or on mount).
// Accepts the listing ID of the currently visible slide so we can look up
// its position in the full seedIds array (which may differ from the
// resolved-listings array index).
export const ensureNearbyResolved = createEvent<string>(); // listing ID
