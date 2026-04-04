import { Box, Text, Button, UnstyledButton } from '@mantine/core';
import { IconLogin } from '@tabler/icons-react';
import { shadows, gradients } from '@app/styles/theme';

interface LoginPromptCardProps {
  promptText: string;
  actionLabel: string;
  onAction: () => void;
  variant?: 'button' | 'link';
}

export function LoginPromptCard({
  promptText,
  actionLabel,
  onAction,
  variant = 'button',
}: LoginPromptCardProps) {
  return (
    <Box
      style={{
        backgroundColor: 'white',
        borderRadius: 16,
        padding: 24,
        boxShadow: shadows.card,
        textAlign: 'center',
      }}
    >
      <IconLogin size={40} color="#adb5bd" stroke={1.5} />
      <Text c="dimmed" mt="md" size="sm">
        {promptText}
      </Text>
      {variant === 'button' ? (
        <Button
          mt="lg"
          radius={12}
          size="md"
          fullWidth
          onClick={onAction}
          style={{
            background: gradients.primary,
            boxShadow: shadows.button,
          }}
        >
          {actionLabel}
        </Button>
      ) : (
        <UnstyledButton onClick={onAction}>
          <Text c="blue" size="sm" fw={600} mt="xs">
            {actionLabel}
          </Text>
        </UnstyledButton>
      )}
    </Box>
  );
}
