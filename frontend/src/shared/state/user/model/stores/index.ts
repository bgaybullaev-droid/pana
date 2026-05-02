import { createStore } from 'effector';
import type { UserStats } from '../types';

export const $userStats = createStore<UserStats | null>(null);
