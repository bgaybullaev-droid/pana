import { FC } from 'react';
import { RangeSlider, Text, Group, Stack } from '@mantine/core';
import { useTranslation } from 'react-i18next';
import { formatPrice } from '@app/styles/theme';

interface PriceSliderProps {
  value: [number, number];
  onChange: (value: [number, number]) => void;
  min?: number;
  max?: number;
  step?: number;
}

export const PriceSlider: FC<PriceSliderProps> = ({
  value,
  onChange,
  min = 0,
  max = 2000000,
  step = 10000,
}) => {
  const { t } = useTranslation('buyer');
  const formatLabel = (val: number) => `${formatPrice(val)} ${t('common.currencySum')}`;

  return (
    <Stack gap="md">
      <Text size="sm" fw={600}>
        {t('filter.priceRange')}
      </Text>
      <RangeSlider
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={onChange}
        label={formatLabel}
        labelAlwaysOn
        styles={{
          thumb: {
            width: 25,
            height: 25,
            borderRadius: 9,
          },
          track: {
            height: 4,
          },
        }}
      />
      <Group justify="space-between">
        <Text size="xs" c="dimmed">
          {formatPrice(min)} {t('common.currencySum')}
        </Text>
        <Text size="xs" c="dimmed">
          {formatPrice(max)} {t('common.currencySum')}
        </Text>
      </Group>
    </Stack>
  );
};
