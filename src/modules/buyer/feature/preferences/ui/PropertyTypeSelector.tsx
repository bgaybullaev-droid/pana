import { SimpleGrid, Box, Text, UnstyledButton } from "@mantine/core";
import {
	IconBuildingSkyscraper,
	IconHome2,
	IconBuildingCommunity,
	IconTrees,
} from "@tabler/icons-react";
import { transitions } from "@app/styles/theme";

interface PropertyTypeSelectorProps {
	value: string[];
	onChange: (value: string[]) => void;
	labels: Record<string, string>;
}

const TYPES = [
	{
		value: "apartment",
		icon: IconBuildingSkyscraper,
		color: "#228be6",
		bg: "#e7f5ff",
	},
	{ value: "house", icon: IconHome2, color: "#40c057", bg: "#ebfbee" },
	{
		value: "commercial",
		icon: IconBuildingCommunity,
		color: "#ff922b",
		bg: "#fff4e6",
	},
	{ value: "land", icon: IconTrees, color: "#be4bdb", bg: "#f3f0ff" },
] as const;

export function PropertyTypeSelector({
	value,
	onChange,
	labels,
}: PropertyTypeSelectorProps) {
	const toggle = (type: string) => {
		if (value.includes(type)) {
			onChange(value.filter((v) => v !== type));
		} else {
			onChange([...value, type]);
		}
	};

	return (
		<SimpleGrid cols={4} spacing={10}>
			{TYPES.map(({ value: type, icon: Icon, color, bg }) => {
				const selected = value.includes(type);
				return (
					<UnstyledButton key={type} onClick={() => toggle(type)}>
						<Box
							style={{
								position: "relative",
								backgroundColor: selected ? bg : "#f8f9fa",
								borderRadius: 14,
								padding: "14px 4px 12px",
								textAlign: "center",
								border: selected
									? `2px solid ${color}`
									: "2px solid transparent",
								transition: transitions.spring,
								transform: selected ? "translateY(-1px)" : "none",
								boxShadow: selected
									? `0 4px 12px ${color}20`
									: "0 1px 3px rgba(0,0,0,0.04)",
							}}
						>
							<Box
								style={{
									width: 40,
									height: 40,
									borderRadius: 12,
									backgroundColor: selected ? `${color}20` : "white",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									margin: "0 auto 8px",
									transition: transitions.fast,
								}}
							>
								<Icon size={20} color={color} stroke={1.8} />
							</Box>
							<Text
								size="10px"
								fw={600}
								c={selected ? color : "gray.7"}
								lh={1.2}
							>
								{labels[type] || type}
							</Text>
						</Box>
					</UnstyledButton>
				);
			})}
		</SimpleGrid>
	);
}
