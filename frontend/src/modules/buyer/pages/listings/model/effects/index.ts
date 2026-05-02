import { createEffect } from 'effector';
import { fetchBuyerListings } from '@shared/api/buyerListings';

export const fetchListingsFx = createEffect(fetchBuyerListings);
