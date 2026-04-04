import { FC, ReactNode } from 'react';
import { Box } from '@mantine/core';
import type { TablerIconsProps } from '@tabler/icons-react';
import { GradientHeader } from './GradientHeader';
import { LoginPromptCard } from './LoginPromptCard';

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
  return (
    <Box mih="100vh" bg="#f8f9fa">
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
