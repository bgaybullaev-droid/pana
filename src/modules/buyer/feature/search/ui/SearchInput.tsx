import { FC } from "react";
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
	return (
		<TextInput
			placeholder={t("home.searchPlaceholder")}
			value={value}
			onChange={(e) => onChange(e.currentTarget.value)}
			onKeyDown={(e) => {
				if (e.key === "Enter") {
					onSubmit();
				}
			}}
			radius={10}
			styles={{
				input: {
					height: 39,
					backgroundColor: "#FFFFFF",
					paddingLeft: 42,
				},
			}}
			leftSection={
				<ActionIcon variant="transparent" size={34} onClick={onBack}>
					<IconArrowLeft size={16} color="#2E3A59" />
				</ActionIcon>
			}
			rightSection={
				value && (
					<ActionIcon variant="transparent" onClick={onClear}>
						<IconX size={18} />
					</ActionIcon>
				)
			}
		/>
	);
};
