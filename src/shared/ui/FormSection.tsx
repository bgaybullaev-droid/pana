import { ReactNode } from 'react';
import { Box, Text, Stack } from '@mantine/core';
import { radii, shadows, spacing, surface } from '@app/styles/theme';

interface FormSectionProps {
  title: string;
  children: ReactNode;
}

export function FormSection({ title, children }: FormSectionProps) {
  return (
    <Box>
      <Text
        size="xs"
        fw={600}
        c="dimmed"
        tt="uppercase"
        mb={8}
        style={{ letterSpacing: 0.5 }}
      >
        {title}
      </Text>
      <Box
        style={{
          backgroundColor: surface.card,
          borderRadius: radii.md,
          padding: spacing.card,
          boxShadow: shadows.sm,
        }}
      >
        <Stack gap="sm">
          {children}
        </Stack>
      </Box>
    </Box>
  );
}
