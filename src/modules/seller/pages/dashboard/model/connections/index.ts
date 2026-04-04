import { sample } from 'effector';
import { pageMounted } from '../events';
import { fetchSellerProfileFx } from '../effects';

sample({
  clock: pageMounted,
  target: fetchSellerProfileFx,
});
