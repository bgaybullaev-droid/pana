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
    <Box 
      className="mesh-gradient"
      style={{ 
        minHeight: 'calc(100dvh - 65px)',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <GradientHeader 
        icon={icon} 
        title={title} 
        onBack={onBack} 
        gradient="transparent"
      />

      <Box px="md" style={{ flex: 1, marginTop: 48 }}>
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
