import { createEvent } from 'effector';
import type { UserPreferences } from '@shared/api/types';

export const preferencesLoaded = createEvent<UserPreferences>();
