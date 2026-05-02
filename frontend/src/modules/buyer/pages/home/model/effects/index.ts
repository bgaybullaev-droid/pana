import { createEffect } from 'effector';
import { fetchUnifiedFeed, UnifiedFeedParams } from '@shared/api/crawlerListings';

export const fetchFeedFx = createEffect(
  async (params: UnifiedFeedParams) => {
    return await fetchUnifiedFeed(params);
  }
);
