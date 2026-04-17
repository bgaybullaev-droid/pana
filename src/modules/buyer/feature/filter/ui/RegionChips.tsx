import { FC } from "react";
import { Chip, Group, Text } from "@mantine/core";
import type { Region } from "@shared/api/types";
import { bucketCount, type FacetBucket } from "@shared/api/facets";

interface RegionChipsProps {
	regions: Region[];
	selected: string[];
	onChange: (id: string) => void;
	/** PR-C — optional facet bucket array for the `region` dimension.
	 *  When present, each chip renders a count suffix like "Tashkent · 312".
	 *  Omitted or empty → chips render plain names, matching legacy UX. */
	facetBuckets?: FacetBucket[];
}

export const RegionChips: FC<RegionChipsProps> = ({
	regions,
	selected,
	onChange,
	facetBuckets,
}) => {
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
					{regions.map((region) => {
						const count = facetBuckets
							? bucketCount(facetBuckets, region.id)
							: 0;
						const showCount = facetBuckets !== undefined && count > 0;
						return (
							<Chip
								key={region.id}
								value={region.id}
								variant="filled"
								radius={17}
								styles={{
									label: {
										height: 34,
										padding: "0 17px",
										fontSize: 12,
										fontWeight: 600,
										textTransform: "capitalize",
										textAlign: "center",
										lineHeight: "34px",
										backgroundColor: selected.includes(region.id)
											? "#FF6E01"
											: "#F1F1F1",
										color: selected.includes(region.id) ? "#FFFFFF" : "#9F9F9F",
										border: "none",
									},
									iconWrapper: { display: "none" },
								}}
							>
								{showCount ? `${region.name} · ${count}` : region.name}
							</Chip>
						);
					})}
				</Group>
			</Chip.Group>
		</div>
	);
};
