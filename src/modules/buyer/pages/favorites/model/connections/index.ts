import { sample } from 'effector';
import { getApiError } from '@shared/api/client';
import { logoutFx } from '@shared/state/auth/model';
import { fetchFavoritesFx, removeFavoriteFx } from '../effects';
import { fetchFavorites, removeFavorite } from '../events';
import { $favorites, $error } from '../stores';

// Wire .on() handlers
$favorites
  .on(fetchFavoritesFx.doneData, (_, favorites) => favorites)
  .on(removeFavoriteFx.done, (state, { result: listingId }) =>
    state.filter((item) => item.id !== listingId)
  )
  .reset(logoutFx.done);

$error.on(fetchFavoritesFx.failData, (_, error) => getApiError(error).message);

// Sample connections
sample({
  clock: fetchFavorites,
  target: fetchFavoritesFx,
});

sample({
  clock: removeFavorite,
  target: removeFavoriteFx,
});
