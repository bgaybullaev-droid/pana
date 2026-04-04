import { sample } from 'effector';
import { $isAuthenticated, $user, setUser } from '@shared/state/auth/model';
import { fetchPreferencesFx, savePreferencesFx } from '../effects';
import { preferencesLoaded } from '../events';

// When preferences are fetched, fire the loaded event
sample({
  clock: fetchPreferencesFx.doneData,
  target: preferencesLoaded,
});

// After saving, mark onboarding_completed on the local user object
savePreferencesFx.doneData.watch(() => {
  const user = $user.getState();
  if (user) {
    setUser({ ...user, onboarding_completed: true });
  }
});

// Fetch preferences when auth state is resolved
sample({
  clock: $isAuthenticated,
  target: fetchPreferencesFx,
});
