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
  isActive?: boolean;
  badge?: React.ReactNode;
}

export function PreferenceCard({
  icon: Icon,
  iconColor,
  iconBg,
  title,
  description,
  children,
  isActive,
  badge,
}: PreferenceCardProps) {
  return (
    <Box
      style={{
        backgroundColor: surface.card,
        borderRadius: radii.lg,
        padding: spacing.card,
        boxShadow: shadows.md,
        border: isActive ? "1px solid #40c057" : "1px solid transparent",
        transition: "border-color 150ms ease",
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
          <Group gap={6} align="center">
            <Text size="sm" fw={700} lh={1.2}>
              {title}
            </Text>
            {badge}
          </Group>
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
