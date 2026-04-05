import { Box, Group, Text, UnstyledButton } from "@mantine/core";

interface ChipMultiSelectProps {
	label?: string;
	options: { value: string; label: string }[];
	value: string[];
	onChange: (value: string[]) => void;
}

export function ChipMultiSelect({
	label,
	options,
	value,
	onChange,
}: ChipMultiSelectProps) {
	const toggle = (optValue: string) => {
		if (value.includes(optValue)) {
			onChange(value.filter((v) => v !== optValue));
		} else {
			onChange([...value, optValue]);
		}
	};

	return (
		<Box>
			{label && (
				<Text size="sm" fw={500} mb={6}>
					{label}
				</Text>
			)}
			<Group gap={8} wrap="wrap">
				{options.map((opt) => {
					const active = value.includes(opt.value);
					return (
						<UnstyledButton
							key={opt.value}
							onClick={() => toggle(opt.value)}
							style={{
								height: 36,
								padding: "0 16px",
								fontSize: 13,
								fontWeight: 600,
								borderRadius: 18,
								backgroundColor: active ? "#228be6" : "#f1f3f5",
								color: active ? "#fff" : "#495057",
								display: "inline-flex",
								alignItems: "center",
								cursor: "pointer",
								transition: "all 0.15s ease",
							}}
						>
							{opt.label}
						</UnstyledButton>
					);
				})}
			</Group>
		</Box>
	);
}
