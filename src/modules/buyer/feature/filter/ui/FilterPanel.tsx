import { FC } from 'react';
import { Box, Stack, Button, Group, Divider } from '@mantine/core';
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation('buyer');
  const [filterState, regions] = useUnit([$filterState, $regions]);

  const handleApply = () => {
    filtersApplied(filterState);
    onApply?.();
  };

  const handleReset = () => {
    filtersReset();
  };

  return (
    <Box p="md" pb={100} h="100%" style={{ overflowY: "auto" }}>
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

        {/* Fixed Action Buttons Panel */}
        <Box
          style={{
            position: "fixed",
            bottom: 0,
            left: 0,
            right: 0,
            paddingBottom: "env(safe-area-inset-bottom, 0px)",
            zIndex: 10001,
            pointerEvents: "none",
          }}
        >
          <Box
            style={{
              padding: "4px 12px 12px",
              maxWidth: 500,
              margin: "0 auto",
            }}
          >
            <Box
              style={{
                display: "flex",
                alignItems: "center",
                height: 56,
                pointerEvents: "auto",
                gap: "10px",
              }}
            >
              <Button
                style={{ flex: 1 }}
                h="100%"
                radius={100}
                c="#495057"
                fw={600}
                fz={14}
                onClick={handleReset}
                styles={{
                  root: {
                    backgroundColor: "rgba(255, 255, 255, 0.65)",
                    backdropFilter: "blur(20px) saturate(180%)",
                    WebkitBackdropFilter: "blur(20px) saturate(180%)",
                    border: "1px solid rgba(255, 255, 255, 0.5)",
                    boxShadow: "0 4px 15px rgba(0,0,0,0.08)",
                  },
                }}
              >
                {t("filter.reset", { defaultValue: "Сбросить" })}
              </Button>
              <Button
                style={{ flex: 1 }}
                h="100%"
                radius={100}
                bg="#40A7E3"
                c="white"
                fw={600}
                fz={14}
                onClick={handleApply}
                styles={{
                  root: { boxShadow: "0 4px 15px rgba(64, 167, 227, 0.4)" },
                }}
              >
                {t("filter.apply", { defaultValue: "Применить" })}
              </Button>
            </Box>
          </Box>
        </Box>
      </Stack>
    </Box>
  );
};
