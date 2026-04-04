import { sample } from 'effector';
import { toggleFavorite } from '../events';
import { $favoritedIds } from '../stores';
import { addFavoriteFx, removeFavoriteFx } from '../effects';

// Toggle favorite: add if not favorited
sample({
  clock: toggleFavorite,
  source: $favoritedIds,
  filter: (ids, id) => !ids.has(id),
  fn: (_, id) => id,
  target: addFavoriteFx,
});

// Toggle favorite: remove if favorited
sample({
  clock: toggleFavorite,
  source: $favoritedIds,
  filter: (ids, id) => ids.has(id),
  fn: (_, id) => id,
  target: removeFavoriteFx,
});
