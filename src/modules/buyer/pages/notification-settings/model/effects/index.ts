import { createEffect } from "effector";
import { notificationSettingsApi, DEFAULT_NOTIFICATION_SETTINGS } from "@shared/api/notificationSettings";
import { $isAuthenticated } from "@shared/state/auth/model";
import type { NotificationSettings } from "@shared/api/types";

export const fetchNotificationSettingsFx = createEffect(
	async (): Promise<NotificationSettings> => {
		const isAuth = $isAuthenticated.getState();
		if (!isAuth) return DEFAULT_NOTIFICATION_SETTINGS;
		return notificationSettingsApi.get();
	},
);

export const saveNotificationSettingsFx = createEffect(
	async (settings: Partial<NotificationSettings>): Promise<NotificationSettings> => {
		return notificationSettingsApi.update(settings);
	},
);
