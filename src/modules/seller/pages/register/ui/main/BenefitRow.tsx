import { Box, Group, Text } from '@mantine/core';
import type { IconList } from '@tabler/icons-react';

const benefitColorMap: Record<string, { bg: string; fg: string }> = {
  blue: { bg: 'rgba(34,139,230,0.1)', fg: '#228be6' },
  green: { bg: 'rgba(64,192,87,0.1)', fg: '#40c057' },
  orange: { bg: 'rgba(255,146,43,0.1)', fg: '#ff922b' },
};

export function BenefitRow({
  icon: Icon,
  color,
  title,
  description,
}: {
  icon: typeof IconList;
  color: string;
  title: string;
  description: string;
}) {
  const colors = benefitColorMap[color] || benefitColorMap.blue;

  return (
    <Group gap="sm" wrap="nowrap">
      <Box
        style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          backgroundColor: colors.bg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Icon size={22} color={colors.fg} stroke={1.8} />
      </Box>
      <Box style={{ minWidth: 0 }}>
        <Text size="sm" fw={600} truncate>
          {title}
        </Text>
        <Text size="xs" c="dimmed" lh={1.3}>
          {description}
        </Text>
      </Box>
    </Group>
  );
}
