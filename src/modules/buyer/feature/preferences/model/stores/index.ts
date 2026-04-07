import { createStore } from "effector";
import type { UserPreferences } from "@shared/api/types";
import { logoutFx, authenticateWithTelegramFx } from "@shared/state/auth/model";
import { fetchPreferencesFx, savePreferencesFx } from "../effects";

// Stores — start as null; backend fetch loads the real user prefs.
// Using null prevents the auto-save from overwriting backend data
// before the fetch completes.
export const $preferences = createStore<UserPreferences | null>(null)
	.on(fetchPreferencesFx.doneData, (_, data) => data)
	.on(savePreferencesFx.doneData, (_, data) => data)
	.reset(logoutFx.done)
	.reset(authenticateWithTelegramFx);

export const $preferencesLoading = fetchPreferencesFx.pending;
