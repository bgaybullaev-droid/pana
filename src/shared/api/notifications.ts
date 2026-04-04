import { apiClient } from './client';
import type {
  Notification,
  NotificationPreferences,
  PaginatedResponse,
  MessageResponse,
  NotificationMarkReadRequest,
  UnreadCountResponse,
} from './types';

export const notificationsApi = {
  // Get paginated notifications
  getNotifications: async (page = 1, perPage = 20, unreadOnly = false) => {
    const response = await apiClient.get<PaginatedResponse<Notification>>(
      '/notifications',
      {
        params: { page, per_page: perPage, unread_only: unreadOnly },
      }
    );
    return response.data;
  },

  // Get unread count
  getUnreadCount: async () => {
    const response = await apiClient.get<UnreadCountResponse>(
      '/notifications/unread-count'
    );
    return response.data;
  },

  // Mark notifications as read
  markAsRead: async (notificationIds?: string[]) => {
    const data: NotificationMarkReadRequest = {
      notification_ids: notificationIds,
    };
    const response = await apiClient.post<MessageResponse>(
      '/notifications/mark-read',
      data
    );
    return response.data;
  },

  // Delete a notification
  deleteNotification: async (notificationId: string) => {
    const response = await apiClient.delete<MessageResponse>(
      `/notifications/${notificationId}`
    );
    return response.data;
  },

  // Get notification preferences
  getPreferences: async () => {
    const response = await apiClient.get<NotificationPreferences>(
      '/notifications/preferences'
    );
    return response.data;
  },

  // Update notification preferences
  updatePreferences: async (data: Partial<NotificationPreferences>) => {
    const response = await apiClient.put<NotificationPreferences>(
      '/notifications/preferences',
      data
    );
    return response.data;
  },
};
