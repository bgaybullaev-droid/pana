import { Box, Button, Stack, Text } from '@mantine/core';
import { type TablerIconsProps } from '@tabler/icons-react';
import { type FC } from 'react';

interface EmptyStateProps {
  icon: FC<TablerIconsProps>;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({ icon: Icon, title, description, actionLabel, onAction }: EmptyStateProps) {
  return (
    <Stack align="center" gap="md" py="xl">
      <Box
        style={{
          width: 80,
          height: 80,
          borderRadius: '50%',
          backgroundColor: 'var(--mantine-color-blue-0)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon size={36} color="var(--mantine-color-blue-4)" stroke={1.5} />
      </Box>
      <Box ta="center">
        <Text fw={600} size="md">
          {title}
        </Text>
        {description && (
          <Text size="sm" c="dimmed" mt={4}>
            {description}
          </Text>
        )}
      </Box>
      {actionLabel && onAction && (
        <Button
          onClick={onAction}
          style={{
            background: 'linear-gradient(135deg, #228be6, #40A7E3)',
            border: 'none',
            boxShadow: '0 4px 12px rgba(34,139,230,0.3)',
          }}
          radius="xl"
          size="md"
        >
          {actionLabel}
        </Button>
      )}
    </Stack>
  );
}
