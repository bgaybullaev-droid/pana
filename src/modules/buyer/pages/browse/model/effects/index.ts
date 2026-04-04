import { createEffect } from 'effector';
import { fetchBuyerListings, toggleListingLike } from '@shared/api/buyerListings';

export const fetchListingsFx = createEffect(fetchBuyerListings);
export const toggleLikeFx = createEffect(toggleListingLike);
