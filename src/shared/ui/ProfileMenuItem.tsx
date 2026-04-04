import { FC } from 'react';
import { Box, Group, Text, UnstyledButton } from '@mantine/core';
import { IconChevronRight } from '@tabler/icons-react';
import type { TablerIconsProps } from '@tabler/icons-react';

interface ProfileMenuItemProps {
  icon: FC<TablerIconsProps>;
  label: string;
  color: string;
  bg: string;
  onClick: () => void;
  showBorder?: boolean;
}

export function ProfileMenuItem({
  icon: Icon,
  label,
  color,
  bg,
  onClick,
  showBorder = true,
}: ProfileMenuItemProps) {
  return (
    <UnstyledButton onClick={onClick} style={{ display: 'block', width: '100%' }}>
      <Group
        justify="space-between"
        px={16}
        py={14}
        style={{
          borderBottom: showBorder ? '1px solid #f1f3f5' : 'none',
        }}
      >
        <Group gap={12}>
          <Box
            style={{
              width: 36,
              height: 36,
              borderRadius: 10,
              backgroundColor: bg,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <Icon size={18} color={color} stroke={2} />
          </Box>
          <Text fw={500} size="sm">
            {label}
          </Text>
        </Group>
        <IconChevronRight size={18} color="#ced4da" />
      </Group>
    </UnstyledButton>
  );
}
