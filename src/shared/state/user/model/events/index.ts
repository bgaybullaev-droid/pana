import { createEvent } from 'effector';

export const fetchUserStats = createEvent();
export const startPolling = createEvent();
export const stopPolling = createEvent();
