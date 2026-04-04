import { createEvent } from 'effector';
import type { ListingCreateData, ListingUpdateData } from '../types';

export const createListing = createEvent<ListingCreateData>();
export const updateListing = createEvent<{ id: string; data: ListingUpdateData }>();
export const fetchListingForEdit = createEvent<string>();
export const resetCreateState = createEvent();
export const resetEditState = createEvent();
