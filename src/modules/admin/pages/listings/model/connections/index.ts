import { sample } from 'effector';
import { pageMounted } from '../events';
import { fetchListingsFx } from '../effects';

sample({
  clock: pageMounted,
  target: fetchListingsFx,
});
