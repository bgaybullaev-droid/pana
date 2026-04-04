import { createEffect } from 'effector';
import { notificationsApi } from '@shared/api/notifications';

export const fetchUserStatsFx = createEffect(async () => {
  const { unread_count } = await notificationsApi.getUnreadCount();
  return {
    favoritesCount: 0,
    unreadCount: unread_count,
    savedSearchesCount: 0,
  };
});
