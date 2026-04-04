import { FC, ReactNode } from "react";
import { Box, Text, UnstyledButton, Badge } from "@mantine/core";
import { IconChevronRight } from "@tabler/icons-react";
import type { TablerIconsProps } from "@tabler/icons-react";

interface SettingsRowProps {
	icon?: FC<TablerIconsProps>;
	label: string;
	onClick: () => void;
	rightValue?: string;
	rightElement?: ReactNode;
	showDivider?: boolean;
	variant?: "default" | "soon" | "destructive";
	destructiveWeight?: 500 | 400;
}

export function SettingsRow({
	icon: Icon,
	label,
	onClick,
	rightValue,
	rightElement,
	showDivider = true,
	variant = "default",
	destructiveWeight = 500,
}: SettingsRowProps) {
	const isSoon = variant === "soon";
	const isDestructive = variant === "destructive";

	return (
		<UnstyledButton
			onClick={onClick}
			style={{ display: "block", width: "100%" }}
		>
			<Box
				style={{
					height: 52,
					display: "flex",
					alignItems: "center",
					paddingLeft: 16,
					paddingRight: 16,
					opacity: isSoon ? 0.45 : 1,
					transition: "background-color 0.1s ease",
				}}
				className="settings-row"
			>
				{Icon && !isDestructive && (
					<Box
						style={{
							width: 22,
							height: 22,
							flexShrink: 0,
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
						}}
					>
						<Icon size={22} stroke={1.5} color="#3C3C43" />
					</Box>
				)}

				<Text
					style={{
						flex: 1,
						marginLeft: Icon && !isDestructive ? 12 : 0,
						fontSize: 16,
						fontWeight: isDestructive ? destructiveWeight : 400,
						color: isDestructive ? "#FF3B30" : "#3C3C43",
						lineHeight: "20px",
					}}
				>
					{label}
				</Text>

				{rightElement}

				{rightValue && !isSoon && (
					<Text
						style={{
							fontSize: 15,
							fontWeight: 400,
							color: "#8E8E93",
							marginRight: 6,
						}}
					>
						{rightValue}
					</Text>
				)}

				{isSoon && (
					<Badge
						variant="filled"
						size="sm"
						radius={10}
						styles={{
							root: {
								backgroundColor: "#F2F2F7",
								color: "#8E8E93",
								fontSize: 11,
								fontWeight: 500,
								textTransform: "none",
								padding: "3px 10px",
								height: "auto",
								opacity: 1 / 0.45, // counteract parent opacity
							},
						}}
					>
						Soon
					</Badge>
				)}

				{!isSoon && !isDestructive && (
					<IconChevronRight size={14} color="#C7C7CC" />
				)}
			</Box>

			{showDivider && (
				<Box
					style={{
						height: 0.5,
						backgroundColor: "#E8E8ED",
						marginLeft: 50,
					}}
				/>
			)}
		</UnstyledButton>
	);
}
