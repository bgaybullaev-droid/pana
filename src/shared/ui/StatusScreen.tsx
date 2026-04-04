import { Container, Stack, Text, Button, Box } from '@mantine/core';
import { IconLogout } from '@tabler/icons-react';
import type { TablerIconsProps } from '@tabler/icons-react';

interface StatusScreenProps {
  gradient: string;
  icon: React.ComponentType<TablerIconsProps>;
  title: string;
  subtitle: string;
  description: string;
  secondaryText?: string;
  onAction: () => void;
  actionLabel: string;
}

export function StatusScreen({ gradient, icon: Icon, title, subtitle, description, secondaryText, onAction, actionLabel }: StatusScreenProps) {
  return (
    <Box style={{ minHeight: '100vh', backgroundColor: '#f8f9fa' }}>
      {/* Gradient top */}
      <Box
        style={{
          background: gradient,
          padding: '60px 20px 80px',
          textAlign: 'center',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* Decorative */}
        <Box style={{ position: 'absolute', top: -20, right: -20, width: 100, height: 100, borderRadius: '50%', backgroundColor: 'rgba(255,255,255,0.1)' }} />
        <Box style={{ position: 'absolute', bottom: 10, left: -10, width: 60, height: 60, borderRadius: '50%', backgroundColor: 'rgba(255,255,255,0.08)' }} />

        <Box
          style={{
            width: 88,
            height: 88,
            borderRadius: '50%',
            backgroundColor: 'rgba(255,255,255,0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px',
          }}
        >
          <Icon size={44} color="white" stroke={1.5} />
        </Box>

        <Text size="xl" fw={700} c="white">{title}</Text>
        <Text size="sm" c="rgba(255,255,255,0.85)" mt={4}>{subtitle}</Text>
      </Box>

      {/* Content card */}
      <Container
        size="xs"
        px="md"
        style={{ marginTop: -40, position: 'relative', zIndex: 1 }}
      >
        <Box
          style={{
            backgroundColor: 'white',
            borderRadius: 16,
            padding: 24,
            boxShadow: '0 2px 12px rgba(0,0,0,0.06)',
            textAlign: 'center',
          }}
        >
          <Stack align="center" gap="md">
            <Text size="sm" c="dimmed" style={{ lineHeight: 1.6 }}>{description}</Text>
            {secondaryText && <Text size="xs" c="dimmed">{secondaryText}</Text>}
            <Button
              variant="light"
              color="gray"
              leftSection={<IconLogout size={16} />}
              onClick={onAction}
              radius="xl"
              mt="sm"
            >
              {actionLabel}
            </Button>
          </Stack>
        </Box>
      </Container>
    </Box>
  );
}
