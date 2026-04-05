import { ReactNode } from 'react';
import { Box, Text, Stack } from '@mantine/core';
import { radii, shadows, spacing, surface } from '@app/styles/theme';

interface FormSectionProps {
  title: string;
  children: ReactNode;
}

export function FormSection({ title, children }: FormSectionProps) {
  return (
    <Box
      style={{
        backgroundColor: surface.card,
        borderRadius: radii.md,
        padding: spacing.card,
        boxShadow: shadows.sm,
      }}
    >
      <Text size="xs" fw={600} c="blue.6" tt="uppercase" mb="sm" lh={1}>
        {title}
      </Text>
      <Stack gap="sm">
        {children}
      </Stack>
    </Box>
  );
}
