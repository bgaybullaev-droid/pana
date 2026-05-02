import { Box, Group, Text } from '@mantine/core';
import { radii, shadows, spacing, surface } from '@app/styles/theme';
import { type TablerIconsProps } from '@tabler/icons-react';
import { type FC } from 'react';

interface StatCardProps {
  icon: FC<TablerIconsProps>;
  color: string;
  value: string | number;
  label: string;
  compact?: boolean;
}

const colorMap: Record<string, { bg: string; fg: string }> = {
  blue: { bg: 'rgba(34,139,230,0.1)', fg: '#228be6' },
  green: { bg: 'rgba(64,192,87,0.1)', fg: '#40c057' },
  orange: { bg: 'rgba(255,146,43,0.1)', fg: '#ff922b' },
  red: { bg: 'rgba(250,82,82,0.1)', fg: '#fa5252' },
  teal: { bg: 'rgba(18,184,134,0.1)', fg: '#12b886' },
  cyan: { bg: 'rgba(21,170,191,0.1)', fg: '#15aabf' },
  violet: { bg: 'rgba(121,80,242,0.1)', fg: '#7950f2' },
};

export function StatCard({ icon: Icon, color, value, label, compact }: StatCardProps) {
  const colors = colorMap[color] || colorMap.blue;
  const iconSize = compact ? 40 : 48;
  const iconRadius = radii.md;
  const iconPx = compact ? 18 : 22;
  const padding = compact ? spacing.cardCompact : spacing.card;

  return (
    <Box
      style={{
        background: surface.card,
        borderRadius: radii.lg,
        boxShadow: shadows.md,
        padding,
        transition: 'all 0.2s ease',
        cursor: 'default',
      }}
    >
      <Group gap={compact ? 10 : 12} wrap="nowrap">
        <Box
          style={{
            width: iconSize,
            height: iconSize,
            borderRadius: iconRadius,
            backgroundColor: colors.bg,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Icon size={iconPx} color={colors.fg} stroke={1.8} />
        </Box>
        <Box style={{ minWidth: 0 }}>
          <Text size={compact ? 'lg' : 'xl'} fw={700} lh={1.2} truncate>
            {value}
          </Text>
          <Text size="xs" c="dimmed" lh={1.3} truncate>
            {label}
          </Text>
        </Box>
      </Group>
    </Box>
  );
}
