import { FC, useState } from "react";
import { TextInput, ActionIcon } from "@mantine/core";
import { IconArrowLeft, IconX } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";

interface SearchInputProps {
	value: string;
	onChange: (value: string) => void;
	onBack: () => void;
	onClear: () => void;
	onSubmit: () => void;
}

export const SearchInput: FC<SearchInputProps> = ({
	value,
	onChange,
	onBack,
	onClear,
	onSubmit,
}) => {
	const { t } = useTranslation("buyer");
	const [focused, setFocused] = useState(false);
	return (
		<TextInput
			placeholder={focused ? "" : t("search.title")}
			value={value}
			onChange={(e) => onChange(e.currentTarget.value)}
			onFocus={() => setFocused(true)}
			onBlur={() => setFocused(false)}
			onKeyDown={(e) => {
				if (e.key === "Enter") {
					onSubmit();
				}
			}}
			radius={22}
			styles={{
				input: {
					height: 45,
					backgroundColor: focused ? "#f8f9fa" : "#f1f3f5",
					border: focused ? "1px solid #dee2e6" : "none",
					paddingLeft: 42,
					fontSize: 16,
					transition: "background-color 0.15s ease, border-color 0.15s ease",
				},
			}}
			leftSection={
				<ActionIcon variant="transparent" size={34} onClick={onBack}>
					<IconArrowLeft size={16} color="#2E3A59" />
				</ActionIcon>
			}
			rightSection={
				value ? (
					<ActionIcon
						variant="filled"
						size={18}
						radius="50%"
						color="gray.5"
						onClick={onClear}
					>
						<IconX size={10} color="white" />
					</ActionIcon>
				) : null
			}
		/>
	);
};
