import { createEvent } from 'effector';
import type { BuyerFilterState } from '@shared/api/types';

export const pageOpened = createEvent();
export const loadMore = createEvent();
export const filtersChanged = createEvent<Partial<BuyerFilterState>>();
export const searchChanged = createEvent<string>();
export const resetListings = createEvent();
