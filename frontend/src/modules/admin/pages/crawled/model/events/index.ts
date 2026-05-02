import { createEvent } from 'effector';
import type { CrawledSource } from '../types';

export const pageOpened = createEvent();
export const sourceChanged = createEvent<CrawledSource>();
export const pageChanged = createEvent<number>();
export const propertyTypeChanged = createEvent<string | null>();
export const listingTypeChanged = createEvent<string | null>();
export const resetCrawledState = createEvent();
