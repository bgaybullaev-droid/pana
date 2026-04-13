import { Group, UnstyledButton, Box, Text, useMantineTheme } from "@mantine/core";
import { useTranslation } from "react-i18next";
import {
	IconKey,
	IconCalendarEvent,
	IconBuildingSkyscraper,
	IconHome2,
	IconBuildingCommunity,
	IconTrees,
} from "@tabler/icons-react";

export interface DealTypeGridProps {
	value: string[];
	onChange: (value: string) => void;
}

export function DealTypeGrid({ value, onChange }: DealTypeGridProps) {
	const { t } = useTranslation("buyer");
	const theme = useMantineTheme();
	const surfacePage = "#f8f9fa"; // Fallback if surface.page is not accessible

	const options = [
		{
			value: "sell",
			icon: IconKey,
			color: "#228be6",
			bg: "#e7f5ff",
			label: t("common.sell"),
		},
		{
			value: "rent",
			icon: IconCalendarEvent,
			color: "#40c057",
			bg: "#ebfbee",
			label: t("common.rent"),
		},
	] as const;

	return (
		<Group grow gap={10}>
			{options.map(({ value: optValue, icon: Icon, color, bg, label }) => {
				const selected = value.includes(optValue);
				return (
					<UnstyledButton key={optValue} onClick={() => onChange(optValue)}>
						<Box
							style={{
								backgroundColor: selected ? bg : surfacePage,
								borderRadius: theme.radius.md,
								padding: "18px 12px",
								textAlign: "center",
								border: selected ? `2px solid ${color}` : "2px solid #e9ecef",
								transition: "transform 150ms ease, box-shadow 150ms ease",
								transform: selected ? "translateY(-1px)" : "none",
								boxShadow: selected ? `0 4px 12px ${color}25` : "none",
							}}
						>
							<Box
								style={{
									width: 48,
									height: 48,
									borderRadius: theme.radius.md,
									backgroundColor: selected ? `${color}20` : "white",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									margin: "0 auto 10px",
									transition: "background-color 150ms ease",
								}}
							>
								<Icon size={24} color={color} stroke={1.8} />
							</Box>
							<Text size="sm" fw={600} c={selected ? color : "gray.7"}>
								{label}
							</Text>
						</Box>
					</UnstyledButton>
				);
			})}
		</Group>
	);
}

export interface PropertyTypeGridProps {
	value: string[];
	onChange: (value: string) => void;
}

export function PropertyTypeGrid({ value, onChange }: PropertyTypeGridProps) {
	const { t } = useTranslation("buyer");
	const theme = useMantineTheme();
	const surfacePage = "#f8f9fa";

	const options = [
		{
			value: "apartment",
			icon: IconBuildingSkyscraper,
			color: "#228be6",
			bg: "#e7f5ff",
		},
		{
			value: "house",
			icon: IconHome2,
			color: "#40c057",
			bg: "#ebfbee",
		},
		{
			value: "commercial",
			icon: IconBuildingCommunity,
			color: "#ff922b",
			bg: "#fff4e6",
		},
		{
			value: "land",
			icon: IconTrees,
			color: "#be4bdb",
			bg: "#f3f0ff",
		},
	] as const;

	return (
		<Group grow gap={10}>
			{options.map(({ value: optValue, icon: Icon, color, bg }) => {
				const selected = value.includes(optValue as any);
				return (
					<UnstyledButton key={optValue} onClick={() => onChange(optValue)}>
						<Box
							style={{
								backgroundColor: selected ? bg : surfacePage,
								borderRadius: theme.radius.md,
								padding: "14px 4px 12px",
								textAlign: "center",
								border: selected ? `2px solid ${color}` : "2px solid transparent",
								transition: "transform 150ms ease, box-shadow 150ms ease",
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
									borderRadius: theme.radius.md,
									backgroundColor: selected ? `${color}20` : "white",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									margin: "0 auto 8px",
									transition: "background-color 150ms ease",
								}}
							>
								<Icon size={20} color={color} stroke={1.8} />
							</Box>
							<Text size="10px" fw={600} c={selected ? color : "gray.7"} lh={1.2}>
								{t(`common.propertyType.${optValue}`)}
							</Text>
						</Box>
					</UnstyledButton>
				);
			})}
		</Group>
	);
}
