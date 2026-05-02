import { FC } from 'react';
import { Chip, Group, Text } from '@mantine/core';
import type { SortingOption } from '@shared/api/types';

interface SortingChipsProps {
  options: SortingOption[];
  selected: number;
  onChange: (id: number) => void;
}

export const SortingChips: FC<SortingChipsProps> = ({ options, selected, onChange }) => {
  return (
    <div>
      <Text size="sm" fw={600} mb="xs">
        Sort by
      </Text>
      <Chip.Group
        multiple={false}
        value={selected.toString()}
        onChange={(value) => onChange(Number(value))}
      >
        <Group gap={7} wrap="wrap">
          {options.map((option) => (
            <Chip
              key={option.id}
              value={option.id.toString()}
              variant="filled"
              radius={17}
              styles={{
                label: {
                  height: 34,
                  padding: '0 17px',
                  fontSize: 12,
                  fontWeight: 600,
                  textTransform: 'capitalize',
                  backgroundColor: selected === option.id ? '#FF6E01' : '#F1F1F1',
                  color: selected === option.id ? '#FFFFFF' : '#9F9F9F',
                  border: 'none',
                },
                iconWrapper: { display: 'none' },
              }}
            >
              {option.label}
            </Chip>
          ))}
        </Group>
      </Chip.Group>
    </div>
  );
};
