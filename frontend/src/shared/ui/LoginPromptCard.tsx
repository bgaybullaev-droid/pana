import { Box, Text, Button, UnstyledButton } from '@mantine/core';
import { IconUserCircle } from '@tabler/icons-react';
import { useTranslation } from 'react-i18next';
import { gradients } from '@app/styles/theme';

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
  const { t } = useTranslation('buyer');
  return (
    <Box
      className="glass animate-fade-in"
      style={{
        borderRadius: 28,
        padding: 28,
        boxShadow: "0 20px 40px rgba(0,0,0,0.08)",
        textAlign: 'center',
        border: "1px solid rgba(255, 255, 255, 0.4)",
        position: "relative",
        overflow: "hidden",
      }}
    >

      
      <Box style={{ position: "relative", zIndex: 1 }}>
        <Box
          style={{
            width: 64,
            height: 64,
            borderRadius: 20,
            background: "linear-gradient(135deg, #228be6, #4dabf7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 16px",
            boxShadow: "0 8px 16px rgba(34,139,230,0.25)",
          }}
        >
          <IconUserCircle size={32} color="white" stroke={1.5} />
        </Box>
        <Text size="lg" fw={700} mb={4}>
          {actionLabel === t("common.login") ? t("auth.loginTitle") || "Вход" : actionLabel}
        </Text>
        <Text c="dimmed" size="sm" px="md" mb={24}>
          {promptText}
        </Text>
      {variant === 'button' ? (
        <Button
          radius="xl"
          size="lg"
          fullWidth
          onClick={onAction}
          style={{
            background: gradients.primary,
            boxShadow: "0 8px 20px rgba(25, 113, 194, 0.25)",
            height: 54,
            fontWeight: 700,
          }}
        >
          {actionLabel}
        </Button>
      ) : (
        <UnstyledButton onClick={onAction}>
          <Text c="blue" size="md" fw={700}>
            {actionLabel}
          </Text>
        </UnstyledButton>
      )}
      </Box>
    </Box>
  );
}
