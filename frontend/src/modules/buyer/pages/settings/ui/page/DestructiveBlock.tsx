import { Box } from "@mantine/core";
import { SettingsRow } from "./SettingsRow";

interface DestructiveBlockProps {
	logoutLabel: string;
	deleteLabel: string;
	onLogout: () => void;
	onDelete: () => void;
}

export function DestructiveBlock({
	logoutLabel,
	deleteLabel,
	onLogout,
	onDelete,
}: DestructiveBlockProps) {
	return (
		<Box style={{ marginTop: 32 }}>
			<Box
				style={{
					backgroundColor: "#FFFFFF",
					borderRadius: 14,
					marginLeft: 16,
					marginRight: 16,
					overflow: "hidden",
				}}
			>
				<SettingsRow
					label={logoutLabel}
					onClick={onLogout}
					variant="destructive"
					destructiveWeight={500}
					showDivider
				/>
				<SettingsRow
					label={deleteLabel}
					onClick={onDelete}
					variant="destructive"
					destructiveWeight={400}
					showDivider={false}
				/>
			</Box>
		</Box>
	);
}
