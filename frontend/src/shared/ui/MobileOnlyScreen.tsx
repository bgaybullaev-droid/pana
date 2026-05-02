import { Container, Text, Title, Stack, ThemeIcon } from '@mantine/core';
import { IconDeviceMobile } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';

export function MobileOnlyScreen() {
  const { t } = useTranslation('buyer');
  return (
    <Container
      size="xs"
      style={{
        height: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Stack align="center" gap="lg">
        <ThemeIcon size={80} radius="xl" variant="light" color="blue">
          <IconDeviceMobile size={48} />
        </ThemeIcon>

        <Title order={2} ta="center">
          {t('mobileOnly.title')}
        </Title>

        <Text c="dimmed" ta="center" size="lg">
          {t('mobileOnly.description')}
        </Text>

        <Text c="dimmed" ta="center">
          {t('mobileOnly.instruction')}
        </Text>
      </Stack>
    </Container>
  );
}
