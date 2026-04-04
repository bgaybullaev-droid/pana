import { UnstyledButton, Box, Text } from '@mantine/core';
import type { IconPlus } from '@tabler/icons-react';

interface QuickActionProps {
  icon: typeof IconPlus;
  label: string;
  onClick: () => void;
}

export function QuickAction({ icon: Icon, label, onClick }: QuickActionProps) {
  return (
    <UnstyledButton onClick={onClick} style={{ width: '100%' }}>
      <Box
        style={{
          border: '1.5px solid var(--mantine-color-gray-2)',
          borderRadius: 12,
          padding: '14px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          transition: 'all 0.2s ease',
        }}
      >
        <Icon size={22} color="var(--mantine-color-gray-6)" stroke={1.5} />
        <Text size="sm" fw={500} c="gray.7">
          {label}
        </Text>
      </Box>
    </UnstyledButton>
  );
}
