import { useState } from "react";
import { Box, Group, Text, TextInput, UnstyledButton } from "@mantine/core";
import { useTranslation } from "react-i18next";

interface ChipSelectProps {
	label?: string;
	options: { value: string; label: string }[];
	value: string | number | undefined;
	onChange: (value: string | number | undefined) => void;
	customInputMode?: "numeric" | "decimal" | "text";
	customPlaceholder?: string;
	required?: boolean;
	error?: string | null;
}

function ChipButton({
	label,
	active,
	dashed,
	onClick,
}: {
	label: string;
	active: boolean;
	dashed?: boolean;
	onClick: () => void;
}) {
	return (
		<UnstyledButton
			onClick={onClick}
			style={{
				height: 36,
				padding: "0 16px",
				fontSize: 13,
				fontWeight: 600,
				borderRadius: 18,
				backgroundColor: active ? "#228be6" : "#f1f3f5",
				color: active ? "#fff" : "#495057",
				border: !active && dashed ? "1px dashed #ced4da" : "none",
				display: "inline-flex",
				alignItems: "center",
				cursor: "pointer",
				transition: "all 0.15s ease",
			}}
		>
			{label}
		</UnstyledButton>
	);
}

export function ChipSelect({
	label,
	options,
	value,
	onChange,
	customInputMode,
	customPlaceholder,
	required,
	error,
}: ChipSelectProps) {
	const { t } = useTranslation("seller");

	const stringVal = value != null ? String(value) : "";
	const isPredefined = options.some((o) => o.value === stringVal);

	// "Other" mode: explicitly toggled by the user, OR auto-detected when
	// the current value doesn't match any predefined option.
	const [otherOpen, setOtherOpen] = useState(false);
	const [customText, setCustomText] = useState("");

	// The custom input is visible when:
	// 1. User explicitly clicked "Other", OR
	// 2. The current value exists but isn't in the predefined list (editing existing data)
	const isCustomValue = stringVal !== "" && !isPredefined;
	const showCustomInput = otherOpen || isCustomValue;

	const handleOptionClick = (optValue: string) => {
		// Toggle: click same option → deselect
		if (stringVal === optValue) {
			onChange(undefined);
			return;
		}
		// Select predefined → close "Other" mode
		setOtherOpen(false);
		setCustomText("");
		if (customInputMode === "numeric" || customInputMode === "decimal") {
			const num = Number(optValue);
			onChange(isNaN(num) ? optValue : num);
		} else {
			onChange(optValue);
		}
	};

	const handleOtherClick = () => {
		if (otherOpen) {
			// Close "Other": clear custom value
			setOtherOpen(false);
			setCustomText("");
			onChange(undefined);
		} else {
			// Open "Other": clear predefined selection
			setOtherOpen(true);
			onChange(undefined);
		}
	};

	const handleCustomChange = (text: string) => {
		let filtered = text;
		if (customInputMode === "numeric") {
			filtered = text.replace(/[^0-9-]/g, "");
		} else if (customInputMode === "decimal") {
			filtered = text.replace(/[^0-9.-]/g, "");
		}
		setCustomText(filtered);

		if (filtered === "") {
			onChange(undefined);
		} else if (customInputMode === "numeric" || customInputMode === "decimal") {
			const num = Number(filtered);
			onChange(isNaN(num) ? undefined : num);
		} else {
			onChange(filtered);
		}
	};

	return (
		<Box>
			{label && (
				<Text size="sm" fw={500} mb={6}>
					{label}
					{required && (
						<Text span c="red" inherit>
							{" "}
							*
						</Text>
					)}
				</Text>
			)}
			<Group gap={8} wrap="wrap">
				{options.map((opt) => (
					<ChipButton
						key={opt.value}
						label={opt.label}
						active={isPredefined && stringVal === opt.value}
						onClick={() => handleOptionClick(opt.value)}
					/>
				))}
				{customInputMode && (
					<ChipButton
						label={t("createListing.other", { ns: "seller" })}
						active={showCustomInput}
						dashed={!showCustomInput}
						onClick={handleOtherClick}
					/>
				)}
			</Group>

			{/* Custom input — visible only when "Other" is active */}
			{customInputMode && (
				<Box
					style={{
						maxHeight: showCustomInput ? 60 : 0,
						opacity: showCustomInput ? 1 : 0,
						overflow: "hidden",
						transition: "max-height 0.2s ease, opacity 0.2s ease",
					}}
				>
					<TextInput
						mt={10}
						placeholder={
							customPlaceholder ||
							t("createListing.enterValue", { ns: "seller" })
						}
						inputMode={customInputMode}
						value={isCustomValue ? stringVal : customText}
						onChange={(e) => handleCustomChange(e.currentTarget.value)}
						autoFocus={showCustomInput}
						radius="md"
						styles={{
							input: { height: 40, fontSize: 14 },
						}}
					/>
				</Box>
			)}

			{error && (
				<Text size="xs" c="red" mt={4}>
					{error}
				</Text>
			)}
		</Box>
	);
}
