import { createEvent } from 'effector';
import type { BuyerListing } from '@shared/api/types';

export const searchQueryChanged = createEvent<string>();
export const searchSubmitted = createEvent<string>();
export const historyItemRemoved = createEvent<string>();
export const historyCleared = createEvent();
export const resultSelected = createEvent<BuyerListing>();
