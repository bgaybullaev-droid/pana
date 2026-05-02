import { Group, Box, Text, UnstyledButton } from "@mantine/core";
import { IconKey, IconCalendarEvent } from "@tabler/icons-react";
import { transitions } from "@app/styles/theme";

interface ListingTypeSelectorProps {
	value: string[];
	onChange: (value: string[]) => void;
	buyLabel: string;
	rentLabel: string;
}

const TYPES = [
	{ value: "sell", icon: IconKey, color: "#228be6", bg: "#e7f5ff" },
	{ value: "rent", icon: IconCalendarEvent, color: "#40c057", bg: "#ebfbee" },
] as const;

export function ListingTypeSelector({
	value,
	onChange,
	buyLabel,
	rentLabel,
}: ListingTypeSelectorProps) {
	const labels: Record<string, string> = { sell: buyLabel, rent: rentLabel };

	const toggle = (type: string) => {
		if (value.includes(type)) {
			onChange(value.filter((v) => v !== type));
		} else {
			onChange([...value, type]);
		}
	};

	return (
		<Group grow gap={10}>
			{TYPES.map(({ value: type, icon: Icon, color, bg }) => {
				const selected = value.includes(type);
				return (
					<UnstyledButton key={type} onClick={() => toggle(type)}>
						<Box
							style={{
								position: "relative",
								backgroundColor: selected ? bg : "#f8f9fa",
								borderRadius: 14,
								padding: "18px 12px",
								textAlign: "center",
								border: selected ? `2px solid ${color}` : "2px solid #e9ecef",
								transition: transitions.spring,
								transform: selected ? "translateY(-1px)" : "none",
								boxShadow: selected ? `0 4px 12px ${color}25` : "none",
							}}
						>
							<Box
								style={{
									width: 48,
									height: 48,
									borderRadius: 14,
									backgroundColor: selected ? `${color}20` : "white",
									display: "flex",
									alignItems: "center",
									justifyContent: "center",
									margin: "0 auto 10px",
									transition: transitions.fast,
								}}
							>
								<Icon size={24} color={color} stroke={1.8} />
							</Box>
							<Text size="sm" fw={600} c={selected ? color : "gray.7"}>
								{labels[type]}
							</Text>
						</Box>
					</UnstyledButton>
				);
			})}
		</Group>
	);
}
