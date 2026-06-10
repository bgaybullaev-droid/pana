import { ReactNode } from 'react';
import { Box, Group, Text, Stack } from '@mantine/core';
import { IconAlertCircle, IconCircleCheck } from '@tabler/icons-react';
import { radii, shadows, spacing, surface } from '@app/styles/theme';

interface FormSectionProps {
  title: ReactNode;
  required?: boolean;
  children: ReactNode;
  bg?: string;
  /**
   * Completeness state of the section (listing form). When omitted the
   * section renders exactly as before — no border, no header indicator —
   * so existing call sites (seller profile, buyer search) are unaffected.
   */
  status?: 'neutral' | 'complete' | 'error';
  /** Short header indicator text, e.g. «Заполнено» / «Осталось 2». */
  statusLabel?: ReactNode;
}

const STATUS_BORDER: Record<NonNullable<FormSectionProps['status']>, string> = {
  neutral: 'transparent',
  complete: '#69db7c',
  error: '#fa5252',
};

export function FormSection({ title, required, children, bg, status, statusLabel }: FormSectionProps) {
  return (
    <Box>
      <Group justify="space-between" mb={8} gap={8}>
        <Text
          size="xs"
          fw={600}
          c="dimmed"
          tt="uppercase"
          style={{ letterSpacing: 0.5 }}
        >
          {title}
          {required && <span style={{ color: 'var(--mantine-color-red-filled)' }}> *</span>}
        </Text>
        {status === 'complete' && (
          <Group gap={4} wrap="nowrap">
            <IconCircleCheck size={14} color="#40c057" stroke={2.5} />
            <Text size="xs" fw={600} c="green.7">
              {statusLabel}
            </Text>
          </Group>
        )}
        {status === 'error' && (
          <Group gap={4} wrap="nowrap">
            <IconAlertCircle size={14} color="#fa5252" stroke={2.5} />
            <Text size="xs" fw={600} c="red.7">
              {statusLabel}
            </Text>
          </Group>
        )}
      </Group>
      <Box
        style={{
          backgroundColor: bg || surface.card,
          borderRadius: radii.md,
          padding: spacing.card,
          boxShadow: shadows.sm,
          ...(status !== undefined && {
            border: `1.5px solid ${STATUS_BORDER[status]}`,
            transition: 'border-color 0.2s ease',
          }),
        }}
      >
        <Stack gap={25}>
          {children}
        </Stack>
      </Box>
    </Box>
  );
}
