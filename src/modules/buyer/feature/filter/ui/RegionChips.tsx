import { FC } from 'react';
import { Chip, Group, Text } from '@mantine/core';
import type { Region } from '@shared/api/types';

interface RegionChipsProps {
  regions: Region[];
  selected: string[];
  onChange: (id: string) => void;
}

export const RegionChips: FC<RegionChipsProps> = ({ regions, selected, onChange }) => {
  return (
    <div>
      <Text size="sm" fw={600} mb="xs">
        Regions
      </Text>
      <Chip.Group
        multiple
        value={selected}
        onChange={(values) => {
          // Find which value was toggled
          const added = values.find((v) => !selected.includes(v));
          const removed = selected.find((s) => !values.includes(s));
          if (added) onChange(added);
          if (removed) onChange(removed);
        }}
      >
        <Group gap={5} wrap="wrap">
          {regions.map((region) => (
            <Chip
              key={region.id}
              value={region.id}
              variant="filled"
              radius={17}
              styles={{
                label: {
                  height: 34,
                  padding: '0 17px',
                  fontSize: 12,
                  fontWeight: 600,
                  textTransform: 'capitalize',
                  textAlign: 'center',
                  lineHeight: '34px',
                  backgroundColor: selected.includes(region.id) ? '#FF6E01' : '#F1F1F1',
                  color: selected.includes(region.id) ? '#FFFFFF' : '#9F9F9F',
                  border: 'none',
                },
                iconWrapper: { display: 'none' },
              }}
            >
              {region.name}
            </Chip>
          ))}
        </Group>
      </Chip.Group>
    </div>
  );
};
