import { IconClockHour4 } from '@tabler/icons-react';
import { useAuth } from '@app/providers/useAuth';
import { useTranslation } from 'react-i18next';
import { StatusScreen } from './StatusScreen';

export function PendingApprovalScreen() {
  const { logout } = useAuth();
  const { t } = useTranslation('seller');

  return (
    <StatusScreen
      gradient="linear-gradient(135deg, #ff922b 0%, #ffa94d 50%, #ffd8a8 100%)"
      icon={IconClockHour4}
      title={t('pending.title')}
      subtitle={t('pending.subtitle')}
      description={t('pending.description')}
      secondaryText={t('pending.timeEstimate')}
      onAction={logout}
      actionLabel={t('pending.logout')}
    />
  );
}
