import { FC } from 'react';
import { Box, Stack, Button, ActionIcon, Group, Divider } from '@mantine/core';
import { IconRefresh } from '@tabler/icons-react';
import { useUnit } from 'effector-react';
import { SortingChips } from './SortingChips';
import { RegionChips } from './RegionChips';
import { PriceSlider } from './PriceSlider';
import {
  $filterState,
  $regions,
  sortingOptions,
  sortingChanged,
  priceRangeChanged,
  regionToggled,
  filtersReset,
  filtersApplied,
} from '../model';

interface FilterPanelProps {
  onApply?: () => void;
}

export const FilterPanel: FC<FilterPanelProps> = ({ onApply }) => {
  const [filterState, regions] = useUnit([$filterState, $regions]);

  const handleApply = () => {
    filtersApplied(filterState);
    onApply?.();
  };

  const handleReset = () => {
    filtersReset();
  };

  return (
    <Box p="md" h="95%">
      <Stack justify="space-between" h="100%">
        <Stack gap="xl">
          {/* Sorting */}
          <SortingChips
            options={sortingOptions}
            selected={filterState.sortingSelected}
            onChange={sortingChanged}
          />

          <Divider />

          {/* Price Range */}
          <PriceSlider value={filterState.priceRange} onChange={priceRangeChanged} />

          <Divider />

          {/* Regions */}
          <RegionChips
            regions={regions}
            selected={filterState.regions}
            onChange={regionToggled}
          />
        </Stack>

        {/* Action Buttons */}
        <Stack gap="xs">
          <Group justify="space-between" align="center">
            <ActionIcon variant="subtle" size={32} onClick={handleReset}>
              <IconRefresh size={18} />
            </ActionIcon>
          </Group>

          <Button
            fullWidth
            h={34}
            radius={10}
            bg="#40A7E3"
            fw={500}
            fz={12}
            mt={30}
            mb={10}
            styles={{
              root: {
                border: '1px solid #DCDCDC',
              },
            }}
            onClick={handleApply}
          >
            Apply Filters
          </Button>
        </Stack>
      </Stack>
    </Box>
  );
};
