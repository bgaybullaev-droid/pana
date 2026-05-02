import { ReactNode } from 'react';
import { Box, Text, Stack } from '@mantine/core';
import { radii, shadows, spacing, surface } from '@app/styles/theme';

interface FormSectionProps {
  title: ReactNode;
  required?: boolean;
  children: ReactNode;
  bg?: string;
}

export function FormSection({ title, required, children, bg }: FormSectionProps) {
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
        {required && <span style={{ color: 'var(--mantine-color-red-filled)' }}> *</span>}
      </Text>
      <Box
        style={{
          backgroundColor: bg || surface.card,
          borderRadius: radii.md,
          padding: spacing.card,
          boxShadow: shadows.sm,
        }}
      >
        <Stack gap={25}>
          {children}
        </Stack>
      </Box>
    </Box>
  );
}
