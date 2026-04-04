import { createEvent } from 'effector';
import type { SellerRegistrationData, SellerUpdateData } from '../types';

// Events
export const fetchSellerProfile = createEvent();
export const registerAsSeller = createEvent<SellerRegistrationData>();
export const updateSellerProfile = createEvent<SellerUpdateData>();
export const fetchSellerListings = createEvent<{ page?: number; status?: string }>();
export const pauseListing = createEvent<string>();
export const activateListing = createEvent<string>();
export const deleteListing = createEvent<string>();
export const resetSellerState = createEvent();
