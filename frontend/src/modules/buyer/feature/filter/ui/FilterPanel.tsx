import { FC, useEffect, useState } from "react";
import { Box, Stack, Button, Divider } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { useUnit } from "effector-react";
import { SortingChips } from "./SortingChips";
import { RegionChips } from "./RegionChips";
import { PriceSlider } from "./PriceSlider";
import { getFacets, type FacetsResponse } from "@shared/api/facets";
import {
	$filterState,
	$regions,
	sortingOptions,
	sortingChanged,
	priceRangeChanged,
	regionToggled,
	filtersReset,
	filtersApplied,
} from "../model";

interface FilterPanelProps {
	onApply?: () => void;
}

export const FilterPanel: FC<FilterPanelProps> = ({ onApply }) => {
	const { t } = useTranslation("buyer");
	const [filterState, regions] = useUnit([$filterState, $regions]);

	// PR-C — live facet counts for the chip labels. Request runs in parallel
	// with any /listings fetch; failure degrades to empty object so chips
	// render without counts (see `getFacets` safe-fallback contract).
	const [facets, setFacets] = useState<FacetsResponse>({});
	useEffect(() => {
		let cancelled = false;
		const params: Parameters<typeof getFacets>[0] = {};
		if (filterState.priceRange[0] > 0)
			params.price_min = filterState.priceRange[0];
		if (filterState.priceRange[1] < 2000000)
			params.price_max = filterState.priceRange[1];
		// Do NOT forward the `region` filter when requesting region facets —
		// we want counts for EVERY region under the rest of the filter state,
		// not only the ones already selected (Amazon-style sidebar semantics).

		getFacets(params).then((resp) => {
			if (!cancelled) setFacets(resp);
		});
		return () => {
			cancelled = true;
		};
	}, [filterState.priceRange]);

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
					<PriceSlider
						value={filterState.priceRange}
						onChange={priceRangeChanged}
					/>

					<Divider />

					{/* Regions */}
					<RegionChips
						regions={regions}
						selected={filterState.regions}
						onChange={regionToggled}
						facetBuckets={facets.region}
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
								{t("filter.reset")}
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
								{t("filter.apply")}
							</Button>
						</Box>
					</Box>
				</Box>
			</Stack>
		</Box>
	);
};
