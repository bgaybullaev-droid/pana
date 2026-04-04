import { createEffect } from 'effector';
import { apiClient } from '@shared/api/client';
import type { UserPreferences } from '@shared/api/types';
import { $isAuthenticated } from '@shared/state/auth/model';

const DEFAULT_PREFS: UserPreferences = {
  regions: [], districts: [], property_types: [], listing_types: [],
  price_min: null, price_max: null, rooms: [],
};

export const fetchPreferencesFx = createEffect(async () => {
  const isAuth = $isAuthenticated.getState();
  if (isAuth) {
    const { data } = await apiClient.get<UserPreferences>('/me/preferences');
    return data;
  }
  return DEFAULT_PREFS;
});

// Note: savePreferencesFx references $preferences which creates a circular dependency
// We handle this by using getState() in the effect
export const savePreferencesFx = createEffect(async (prefs: Partial<UserPreferences>) => {
  const isAuth = $isAuthenticated.getState();
  if (isAuth) {
    const { data } = await apiClient.put<UserPreferences>('/me/preferences', prefs);
    return data;
  }
  return prefs as UserPreferences;
});
