import { apiClient } from "./client";
import type { NotificationSettings } from "./types";

const DEFAULT_SETTINGS: NotificationSettings = {
	daily_limit: 10,
	time_windows: ["morning", "afternoon", "evening"],
	sources: {
		saved_searches: true,
		seller_follows: true,
		ai_recs: true,
	},
	paused: false,
};

export const notificationSettingsApi = {
	/** GET /api/v1/notification-settings */
	get: async (): Promise<NotificationSettings> => {
		const { data } = await apiClient.get<NotificationSettings>("/notification-settings");
		return data;
	},

	/** PUT /api/v1/notification-settings */
	update: async (payload: Partial<NotificationSettings>): Promise<NotificationSettings> => {
		const { data } = await apiClient.put<NotificationSettings>("/notification-settings", payload);
		return data;
	},
};

export { DEFAULT_SETTINGS as DEFAULT_NOTIFICATION_SETTINGS };
