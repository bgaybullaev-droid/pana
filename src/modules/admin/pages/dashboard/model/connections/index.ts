import { sample } from 'effector';
import { pageMounted } from '../events';
import { fetchDashboardStatsFx } from '../effects';

sample({
  clock: pageMounted,
  target: fetchDashboardStatsFx,
});
