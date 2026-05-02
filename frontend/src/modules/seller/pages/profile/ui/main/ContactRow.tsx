import { Box, Group, Text } from '@mantine/core';
import type { IconPhone } from '@tabler/icons-react';

export function ContactRow({
  icon: Icon,
  label,
  href,
  children,
}: {
  icon: typeof IconPhone;
  label: string;
  href?: string;
  children?: React.ReactNode;
}) {
  const content = (
    <Group gap="sm" wrap="nowrap">
      <Box
        style={{
          width: 36,
          height: 36,
          borderRadius: 10,
          backgroundColor: 'var(--mantine-color-gray-0)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        <Icon size={18} color="var(--mantine-color-gray-6)" />
      </Box>
      <Text size="sm" truncate style={{ flex: 1 }}>
        {label}
      </Text>
      {children}
    </Group>
  );

  if (href) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" style={{ textDecoration: 'none', color: 'inherit' }}>
        {content}
      </a>
    );
  }

  return content;
}
