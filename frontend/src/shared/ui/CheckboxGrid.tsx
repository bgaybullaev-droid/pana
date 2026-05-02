import { Box, Checkbox, SimpleGrid, Text } from "@mantine/core";

interface CheckboxGridProps {
	label?: string;
	options: { value: string; label: string }[];
	value: string[];
	onChange: (value: string[]) => void;
	columns?: number;
}

export function CheckboxGrid({
	label,
	options,
	value,
	onChange,
	columns = 2,
}: CheckboxGridProps) {
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
				<Text size="sm" fw={500} mb={8}>
					{label}
				</Text>
			)}
			<SimpleGrid cols={columns} spacing={8} verticalSpacing={8}>
				{options.map((opt) => (
					<Checkbox
						key={opt.value}
						label={opt.label}
						checked={value.includes(opt.value)}
						onChange={() => toggle(opt.value)}
						styles={{
							label: { fontSize: 13, fontWeight: 500, cursor: "pointer" },
							input: { cursor: "pointer" },
						}}
					/>
				))}
			</SimpleGrid>
		</Box>
	);
}
