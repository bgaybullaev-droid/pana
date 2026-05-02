import { createEffect } from 'effector';
import { resolveListingById, fetchUnifiedFeed } from '@shared/api/crawlerListings';
import { activityLogApi } from '@shared/api/activityLog';

// Constants
const PER_PAGE = 10;

export const fetchInitialListingFx = createEffect(async (id: string) => {
  const listing = await resolveListingById(id);
  // Ф-78: log view for interest vector (fire-and-forget)
  if (listing) {
    activityLogApi.log({
      action: 'view',
      listing_id: listing.id,
      property_type: (listing as { property_type?: string }).property_type,
    });
  }
  return listing;
});

export const fetchFeedFx = createEffect(
  async ({ page, exclude_id }: { page: number; exclude_id?: string }) => {
    return fetchUnifiedFeed({ page, per_page: PER_PAGE, exclude_id });
  }
);

// Set of IDs currently being fetched — prevents duplicate in-flight requests
export const _inflight = new Set<string>();

// Fetch a small batch of listing details.  Skips IDs already in-flight.
export const fetchListingDetailsFx = createEffect(async (ids: string[]) => {
  // Deduplicate against in-flight requests
  const toFetch = ids.filter((id) => !_inflight.has(id));
  if (toFetch.length === 0) return [];

  toFetch.forEach((id) => _inflight.add(id));
  try {
    const results = await Promise.all(toFetch.map((id) => resolveListingById(id)));
    return results;
  } finally {
    toFetch.forEach((id) => _inflight.delete(id));
  }
});
