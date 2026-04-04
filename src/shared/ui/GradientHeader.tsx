import { FC, ReactNode } from 'react';
import { ActionIcon, Box, Text } from '@mantine/core';
import { IconArrowLeft } from '@tabler/icons-react';
import { gradients } from '@app/styles/theme';
import type { TablerIconsProps } from '@tabler/icons-react';

type GradientType = 'header' | 'primary' | 'orange';

interface GradientHeaderProps {
  icon: FC<TablerIconsProps>;
  title: string;
  subtitle?: string;
  gradient?: GradientType;
  onBack?: () => void;
  children?: ReactNode;
}

const gradientMap: Record<GradientType, string> = {
  header: gradients.header,
  primary: gradients.primary,
  orange: gradients.orange,
};

export function GradientHeader({
  icon: Icon,
  title,
  subtitle,
  gradient = 'header',
  onBack,
  children,
}: GradientHeaderProps) {
  return (
    <Box
      style={{
        background: gradientMap[gradient],
        padding: '48px 20px 60px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Decorative circles */}
      <Box
        style={{
          position: 'absolute',
          top: -30,
          right: -30,
          width: 120,
          height: 120,
          borderRadius: '50%',
          backgroundColor: 'rgba(255,255,255,0.08)',
        }}
      />
      <Box
        style={{
          position: 'absolute',
          bottom: 10,
          left: -20,
          width: 80,
          height: 80,
          borderRadius: '50%',
          backgroundColor: 'rgba(255,255,255,0.06)',
        }}
      />

      {onBack && (
        <ActionIcon
          variant="transparent"
          c="white"
          size={36}
          radius="xl"
          onClick={onBack}
          style={{ position: 'absolute', top: 12, left: 12, zIndex: 2 }}
        >
          <IconArrowLeft size={22} />
        </ActionIcon>
      )}

      {children}

      <Box
        style={{
          width: 72,
          height: 72,
          borderRadius: '50%',
          backgroundColor: 'rgba(255,255,255,0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px',
        }}
      >
        <Icon size={36} color="white" stroke={1.5} />
      </Box>
      <Text size="xl" fw={700} c="white">
        {title}
      </Text>
      {subtitle && (
        <Text size="sm" c="rgba(255,255,255,0.8)" mt={4}>
          {subtitle}
        </Text>
      )}
    </Box>
  );
}
