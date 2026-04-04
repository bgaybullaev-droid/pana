import { useEffect, useRef } from 'react';
import { notifications, type NotificationData } from '@mantine/notifications';
import type { Effect } from 'effector';

/**
 * Watch an effector effect's doneData and show a notification.
 * Optionally call a callback after the notification is shown.
 * The watcher is initialized only once.
 */
export function useEffectorNotification(
  fx: Effect<any, any, any>,
  config: NotificationData,
  onDone?: () => void,
) {
  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    const unwatch = fx.doneData.watch(() => {
      notifications.show(config);
      onDoneRef.current?.();
    });
    return () => unwatch();
  }, [fx]); // eslint-disable-line react-hooks/exhaustive-deps
}
