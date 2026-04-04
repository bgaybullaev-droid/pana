import {
  sortingChanged,
  priceRangeChanged,
  regionToggled,
  regionsSet,
  filtersReset,
} from '../events';
import { $filterState } from '../stores';

// Wire .on() handlers
$filterState
  .on(sortingChanged, (state, sortingId) => ({
    ...state,
    sortingSelected: state.sortingSelected === sortingId ? -1 : sortingId,
  }))
  .on(priceRangeChanged, (state, priceRange) => ({
    ...state,
    priceRange,
  }))
  .on(regionToggled, (state, regionId) => ({
    ...state,
    regions: state.regions.includes(regionId)
      ? state.regions.filter((r) => r !== regionId)
      : [...state.regions, regionId],
  }))
  .on(regionsSet, (state, regions) => ({
    ...state,
    regions,
  }))
  .reset(filtersReset);
