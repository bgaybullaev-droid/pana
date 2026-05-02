import { createEffect } from 'effector';
import { searchListings } from '@shared/api/search';

export const searchFx = createEffect(searchListings);
