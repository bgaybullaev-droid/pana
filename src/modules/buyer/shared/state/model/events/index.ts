import { createEvent } from "effector";

export const toggleFavorite = createEvent<string>();

// Search & filter events shared across buyer pages/layout
export const searchQueryChanged = createEvent<string>();
export const applyFilters = createEvent();
export const clearFilters = createEvent();

// Pre-populate ordered listing IDs (used by home → listing-detail)
export const seedListingIds = createEvent<string[]>();
// Mark whether the seeded list is finite (favorites) or paginatable (feed)
export const seedListingSource = createEvent<"feed" | "finite">();
