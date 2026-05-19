import { createEffect } from 'effector';
import { fetchUnifiedFeed, UnifiedFeedParams } from '@shared/api/crawlerListings';
import { apiClient } from '@shared/api/client';
import type { ListingListItem, PaginatedResponse } from '@shared/api/types';

export const fetchFeedFx = createEffect(
  async (params: UnifiedFeedParams) => {
    return await fetchUnifiedFeed(params);
  }
);

/** F048 — buyer subscriptions tab: listings matching the user's saved searches. */
export const fetchSubscriptionsFeedFx = createEffect(
  async (params: { page: number; per_page: number }): Promise<PaginatedResponse<ListingListItem>> => {
    const res = await apiClient.get<PaginatedResponse<ListingListItem>>(
      '/buyer/feed/subscriptions',
      { params },
    );
    return res.data;
  },
);

/** F077 Phase 2 — buyer recommended tab: personalised top-N. */
export const fetchRecommendedFeedFx = createEffect(
  async (params: { limit: number }): Promise<PaginatedResponse<ListingListItem>> => {
    const res = await apiClient.get<PaginatedResponse<ListingListItem>>(
      '/buyer/feed/recommended',
      { params },
    );
    return res.data;
  },
);
