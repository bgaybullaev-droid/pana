import { createEvent } from 'effector';

// --- Events ---

export const pageOpened = createEvent();
export const tabChanged = createEvent<'olx' | 'telegram'>();
export const pageChanged = createEvent<number>();
export const resetState = createEvent();
