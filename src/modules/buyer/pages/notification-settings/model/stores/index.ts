import { createStore } from "effector";
import type { NotificationSettings } from "@shared/api/types";
import { DEFAULT_NOTIFICATION_SETTINGS } from "@shared/api/notificationSettings";
import { fetchNotificationSettingsFx, saveNotificationSettingsFx } from "../effects";

export const $notificationSettings = createStore<NotificationSettings>(DEFAULT_NOTIFICATION_SETTINGS)
	.on(fetchNotificationSettingsFx.doneData, (_, settings) => settings)
	.on(saveNotificationSettingsFx.doneData, (_, settings) => settings);

export const $notificationSettingsLoading = fetchNotificationSettingsFx.pending;
export const $notificationSettingsSaving = saveNotificationSettingsFx.pending;
