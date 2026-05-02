import { sample } from "effector";
import { $isAuthenticated, $user, setUser } from "@shared/state/auth/model";
import { fetchPreferencesFx, savePreferencesFx } from "../effects";
import { preferencesLoaded } from "../events";

// When preferences are fetched (non-null), fire the loaded event
sample({
	clock: fetchPreferencesFx.doneData,
	filter: Boolean,
	target: preferencesLoaded,
});

// After saving, mark onboarding_completed on the local user object
savePreferencesFx.doneData.watch(() => {
	const user = $user.getState();
	if (user) {
		setUser({ ...user, onboarding_completed: true });
	}
});

// Fetch preferences only when user becomes authenticated
sample({
	clock: $isAuthenticated,
	filter: Boolean,
	target: fetchPreferencesFx,
});
