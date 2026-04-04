import { sample } from 'effector';
import { pageMounted } from '../events';
import { fetchSellerListingsFx } from '../effects';

sample({
  clock: pageMounted,
  target: fetchSellerListingsFx,
});
