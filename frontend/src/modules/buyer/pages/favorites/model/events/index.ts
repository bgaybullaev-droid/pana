import { createEvent } from 'effector';

export const fetchFavorites = createEvent();
export const removeFavorite = createEvent<string>();
