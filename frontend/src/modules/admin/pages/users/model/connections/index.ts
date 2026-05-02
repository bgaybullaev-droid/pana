import { sample } from 'effector';
import { pageMounted } from '../events';
import { fetchUsersFx } from '../effects';

sample({
  clock: pageMounted,
  target: fetchUsersFx,
});
