import { Box, Text, Avatar, UnstyledButton } from "@mantine/core";
import { IconChevronRight } from "@tabler/icons-react";

interface ProfileCardProps {
	name: string;
	phone?: string;
	avatarUrl?: string | null;
	initials: string;
	onEdit: () => void;
	editLabel: string;
}

export function ProfileCard({
	name,
	phone,
	avatarUrl,
	initials,
	onEdit,
	editLabel,
}: ProfileCardProps) {
	return (
		<Box
			style={{
				backgroundColor: "#FFFFFF",
				borderRadius: 12,
				padding: 16,
			}}
		>
			<Box
				style={{
					display: "flex",
					alignItems: "center",
					gap: 12,
				}}
			>
				<Avatar
					src={avatarUrl}
					size={52}
					radius="50%"
					styles={{
						root: {
							flexShrink: 0,
						},
						placeholder: {
							backgroundColor: "#E8F0FE",
							color: "#1A73E8",
							fontSize: 18,
							fontWeight: 600,
						},
					}}
				>
					{initials}
				</Avatar>

				<Box style={{ flex: 1, minWidth: 0 }}>
					<Text
						style={{
							fontSize: 17,
							fontWeight: 600,
							color: "#1C1C1E",
							lineHeight: "22px",
						}}
						truncate
					>
						{name}
					</Text>
					{phone && (
						<Text
							style={{
								fontSize: 14,
								fontWeight: 400,
								color: "#8E8E93",
								lineHeight: "18px",
								marginTop: 2,
							}}
						>
							{phone}
						</Text>
					)}
				</Box>

				<UnstyledButton
					onClick={onEdit}
					style={{
						display: "flex",
						alignItems: "center",
						gap: 4,
						flexShrink: 0,
					}}
				>
					<Text
						style={{
							fontSize: 14,
							fontWeight: 500,
							color: "#1A73E8",
						}}
					>
						{editLabel}
					</Text>
					<IconChevronRight size={14} color="#1A73E8" />
				</UnstyledButton>
			</Box>
		</Box>
	);
}
