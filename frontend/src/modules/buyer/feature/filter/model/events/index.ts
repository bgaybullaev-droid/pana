import { createEvent } from 'effector';
import type { BuyerFilterState } from '@shared/api/types';

export const sortingChanged = createEvent<number>();
export const priceRangeChanged = createEvent<[number, number]>();
export const regionToggled = createEvent<string>();
export const regionsSet = createEvent<string[]>();
export const filtersReset = createEvent();
export const filtersApplied = createEvent<BuyerFilterState>();
