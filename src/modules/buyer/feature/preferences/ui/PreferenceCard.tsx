import { ReactNode } from 'react';
import { Box, Group, Stack, Text, ThemeIcon } from '@mantine/core';
import { radii, shadows, spacing, surface } from '@app/styles/theme';
import type { TablerIconsProps } from '@tabler/icons-react';

interface PreferenceCardProps {
  icon: React.FC<TablerIconsProps>;
  iconColor: string;
  iconBg: string;
  title: string;
  description?: string;
  children: ReactNode;
}

export function PreferenceCard({
  icon: Icon,
  iconColor,
  iconBg,
  title,
  description,
  children,
}: PreferenceCardProps) {
  return (
    <Box
      style={{
        backgroundColor: surface.card,
        borderRadius: radii.lg,
        padding: spacing.card,
        boxShadow: shadows.md,
      }}
    >
      <Group gap={12} mb={description ? 6 : 14} align="center" wrap="nowrap">
        <ThemeIcon
          size={38}
          radius="xl"
          variant="light"
          style={{ backgroundColor: iconBg, color: iconColor, flexShrink: 0 }}
        >
          <Icon size={20} stroke={1.8} />
        </ThemeIcon>
        <Stack gap={2}>
          <Text size="sm" fw={700} lh={1.2}>
            {title}
          </Text>
          {description && (
            <Text size="xs" c="dimmed" lh={1.3}>
              {description}
            </Text>
          )}
        </Stack>
      </Group>
      {children}
    </Box>
  );
}
