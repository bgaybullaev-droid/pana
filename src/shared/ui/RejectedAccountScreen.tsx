import { IconBan } from '@tabler/icons-react';
import { useAuth } from '@app/providers/useAuth';
import { useTranslation } from 'react-i18next';
import { StatusScreen } from './StatusScreen';

export function RejectedAccountScreen() {
  const { logout } = useAuth();
  const { t } = useTranslation('seller');

  return (
    <StatusScreen
      gradient="linear-gradient(135deg, #fa5252 0%, #ff6b6b 50%, #ffa8a8 100%)"
      icon={IconBan}
      title={t('rejected.title')}
      subtitle={t('rejected.subtitle')}
      description={t('rejected.description')}
      secondaryText={t('rejected.contactSupport')}
      onAction={logout}
      actionLabel={t('rejected.logout')}
    />
  );
}
