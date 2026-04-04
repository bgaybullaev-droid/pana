import { createStore } from 'effector';
import type { UserPreferences } from '@shared/api/types';
import { logoutFx, authenticateWithTelegramFx } from '@shared/state/auth/model';
import { fetchPreferencesFx, savePreferencesFx } from '../effects';

const DEFAULT_PREFS: UserPreferences = {
  regions: [], districts: [], property_types: [], listing_types: [],
  price_min: null, price_max: null, rooms: [],
};

// Stores — always start with defaults; backend fetch loads the real user prefs
export const $preferences = createStore<UserPreferences | null>(DEFAULT_PREFS)
  .on(fetchPreferencesFx.doneData, (_, data) => data)
  .on(savePreferencesFx.doneData, (_, data) => data)
  .reset(logoutFx.done)
  .reset(authenticateWithTelegramFx);

export const $preferencesLoading = fetchPreferencesFx.pending;
