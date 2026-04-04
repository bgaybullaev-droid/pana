import { ReactNode } from 'react';
import { Box, Text, Stack } from '@mantine/core';

interface FormSectionProps {
  title: string;
  children: ReactNode;
}

export function FormSection({ title, children }: FormSectionProps) {
  return (
    <Box
      style={{
        backgroundColor: 'white',
        borderRadius: 12,
        padding: 16,
        boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
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
