import { useState } from "react";
import { Box, Group, Text, TextInput, UnstyledButton } from "@mantine/core";
import { useTranslation } from "react-i18next";

interface ChipSelectProps {
	label?: string;
	options: { value: string; label: string; breakAfter?: boolean }[];
	value: string | number | undefined;
	onChange: (value: string | number | undefined) => void;
	customInputMode?: "numeric" | "decimal" | "text";
	customPlaceholder?: string;
	required?: boolean;
	/** Dimmed "необязательно" hint next to the label of non-required fields.
	 *  On by default; pass false where the hint is noise (e.g. fields with
	 *  a pre-selected default, or outside the listing form). */
	showOptionalHint?: boolean;
	error?: string | null;
}

function ChipButton({
	label,
	active,
	onClick,
}: {
	label: string;
	active: boolean;
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
	showOptionalHint = true,
	error,
}: ChipSelectProps) {
	const { t } = useTranslation("seller");

	const stringVal = value != null ? String(value) : "";
	const isPredefined = options.some((o) => o.value === stringVal);

	// Free-form input below the chips: always visible (no "Other" toggle),
	// so the user can tap straight into it and the keyboard opens at once.
	const [customText, setCustomText] = useState("");

	// A value that came from outside the predefined list (e.g. edit-mode
	// pre-fill) is shown in the custom input.
	const isCustomValue = stringVal !== "" && !isPredefined;

	const handleOptionClick = (optValue: string) => {
		// Toggle: click same option → deselect
		if (stringVal === optValue) {
			setCustomText("");
			onChange(undefined);
			return;
		}
		// Select predefined → drop any custom text
		setCustomText("");
		if (customInputMode === "numeric" || customInputMode === "decimal") {
			const num = Number(optValue);
			onChange(isNaN(num) ? optValue : num);
		} else {
			onChange(optValue);
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
					{required ? (
						<Text span c="red" inherit>
							{" "}
							*
						</Text>
					) : (
						showOptionalHint && (
							<Text span c="dimmed" fw={400} size="xs">
								{" "}
								— {t("createListing.optionalHint")}
							</Text>
						)
					)}
				</Text>
			)}
			<Group gap={8} wrap="wrap">
				{options.map((opt) => (
					<div
						key={opt.value}
						style={{
							display: "contents",
						}}
					>
						<ChipButton
							label={opt.label}
							active={isPredefined && stringVal === opt.value}
							onClick={() => handleOptionClick(opt.value)}
						/>
						{opt.breakAfter && <Box style={{ flexBasis: "100%", height: 0 }} />}
					</div>
				))}
			</Group>

			{/* Free-form value — always available right below the chips */}
			{customInputMode && (
				<TextInput
					mt={10}
					placeholder={
						customPlaceholder || t("createListing.enterValue", { ns: "seller" })
					}
					inputMode={customInputMode}
					value={isCustomValue ? stringVal : customText}
					onChange={(e) => handleCustomChange(e.currentTarget.value)}
					radius="md"
					styles={{
						input: { height: 40, fontSize: 14 },
					}}
				/>
			)}

			{error && (
				<Text size="xs" c="red" mt={4}>
					{error}
				</Text>
			)}
		</Box>
	);
}
