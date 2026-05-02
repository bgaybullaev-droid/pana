import { Box, Text, Badge, Group, UnstyledButton } from '@mantine/core';
import { radii, shadows } from '@app/styles/theme';

interface PillTab {
  value: string;
  label: string;
  count?: number;
}

interface PillTabsProps {
  tabs: PillTab[];
  activeValue: string;
  onChange: (value: string) => void;
}

export function PillTabs({ tabs, activeValue, onChange }: PillTabsProps) {
  return (
    <Group gap={8}>
      {tabs.map((tab) => {
        const isActive = activeValue === tab.value;
        return (
          <UnstyledButton key={tab.value} onClick={() => onChange(tab.value)}>
            <Box
              style={{
                padding: '7px 14px',
                borderRadius: radii.xl,
                backgroundColor: isActive ? '#228be6' : 'var(--mantine-color-gray-0)',
                border: isActive ? 'none' : '1px solid var(--mantine-color-gray-2)',
                boxShadow: isActive ? shadows.accent : 'none',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'all 0.2s ease',
              }}
            >
              <Text size="sm" fw={isActive ? 600 : 400} c={isActive ? 'white' : 'gray.7'}>
                {tab.label}
              </Text>
              {tab.count !== undefined && (
                <Badge
                  size="sm"
                  variant={isActive ? 'white' : 'light'}
                  color={isActive ? 'blue' : 'gray'}
                  radius="xl"
                  style={isActive ? { backgroundColor: 'rgba(255,255,255,0.25)', color: 'white' } : {}}
                >
                  {tab.count}
                </Badge>
              )}
            </Box>
          </UnstyledButton>
        );
      })}
    </Group>
  );
}
