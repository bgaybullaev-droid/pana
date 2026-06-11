import { Box, Group, Text, UnstyledButton } from "@mantine/core";
import { useTranslation } from "react-i18next";

interface ChipMultiSelectProps {
	label?: string;
	description?: string;
	options: { value: string; label: string }[];
	value: string[];
	onChange: (value: string[]) => void;
	/** Dimmed "необязательно" hint next to the label (multi-selects are
	 *  always optional). On by default; pass false outside the listing form. */
	showOptionalHint?: boolean;
}

export function ChipMultiSelect({
	label,
	description,
	options,
	value,
	onChange,
	showOptionalHint = true,
}: ChipMultiSelectProps) {
	const { t } = useTranslation("seller");
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
				<Text size="sm" fw={500} mb={description ? 2 : 6}>
					{label}
					{showOptionalHint && (
						<Text span c="dimmed" fw={400} size="xs">
							{" "}
							— {t("createListing.optionalHint")}
						</Text>
					)}
				</Text>
			)}
			{description && (
				<Text size="xs" c="dimmed" mb={6}>
					{description}
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
