import { FC, ReactNode } from 'react';
import { Box, LoadingOverlay } from '@mantine/core';
import type { TablerIconsProps } from '@tabler/icons-react';
import { GradientHeader } from './GradientHeader';
import { LoginPromptCard } from './LoginPromptCard';
import { surface } from '@app/styles/theme';
import { useAuth } from '@app/providers/useAuth';

interface UnauthScreenProps {
  icon: FC<TablerIconsProps>;
  title: string;
  subtitle?: string;
  loginPrompt: string;
  loginLabel: string;
  onLogin: () => void;
  loginVariant?: 'button' | 'link';
  onBack?: () => void;
  children?: ReactNode;
}

export function UnauthScreen({
  icon,
  title,
  subtitle,
  loginPrompt,
  loginLabel,
  onLogin,
  loginVariant = 'button',
  onBack,
  children,
}: UnauthScreenProps) {
  const { isLoading } = useAuth();

  if (isLoading) {
    return (
      <Box mih="100vh" bg={surface.page} pos="relative">
        <LoadingOverlay visible={true} zIndex={1000} overlayProps={{ radius: "sm", blur: 2 }} />
      </Box>
    );
  }

  return (
    <Box mih="100vh" bg={surface.page}>
      <GradientHeader icon={icon} title={title} subtitle={subtitle} onBack={onBack} />

      <Box px="md" style={{ marginTop: -30 }}>
        <LoginPromptCard
          promptText={loginPrompt}
          actionLabel={loginLabel}
          onAction={onLogin}
          variant={loginVariant}
        />
      </Box>

      {children}
    </Box>
  );
}
