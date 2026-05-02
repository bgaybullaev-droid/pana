import { createStore } from 'effector';
import type { BuyerFilterState, Region } from '@shared/api/types';
import { defaultRegions } from '../lib';

// Default filter state
const defaultFilterState: BuyerFilterState = {
  sortingSelected: -1,
  priceRange: [0, 2000000],
  regions: [],
};

export const $filterState = createStore<BuyerFilterState>(defaultFilterState);

export const $regions = createStore<Region[]>(defaultRegions);
