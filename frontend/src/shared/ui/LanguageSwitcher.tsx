import { SegmentedControl } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { radii, surface } from '@app/styles/theme';

interface LanguageSwitcherProps {
  variant?: 'dark' | 'light';
}

export function LanguageSwitcher({ variant = 'dark' }: LanguageSwitcherProps) {
  const { i18n } = useTranslation();

  const styles =
    variant === 'dark'
      ? {
          root: {
            background: 'rgba(255, 255, 255, 0.12)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            padding: 2,
          },
          label: {
            color: 'rgba(255, 255, 255, 0.7)',
            fontWeight: 700,
            fontSize: 11,
            padding: '4px 10px',
          },
          indicator: {
            background: 'rgba(255, 255, 255, 0.22)',
            boxShadow: 'none',
          },
        }
      : {
          root: {
            backgroundColor: surface.muted,
            borderRadius: radii.md,
            padding: 2,
          },
          label: {
            fontWeight: 700,
            fontSize: 12,
            padding: '4px 12px',
          },
          indicator: {
            borderRadius: radii.sm,
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          },
        };

  return (
    <SegmentedControl
      value={i18n.language}
      onChange={(val) => i18n.changeLanguage(val)}
      data={[
        { label: 'RU', value: 'ru' },
        { label: 'UZ', value: 'uz' },
      ]}
      size="xs"
      radius={radii.md}
      styles={styles}
    />
  );
}
