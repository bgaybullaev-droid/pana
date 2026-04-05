import { forwardRef } from "react";
import { Box, UnstyledButton, Text } from "@mantine/core";
import type { IconHome } from "@tabler/icons-react";
import { radii, transitions } from "@app/styles/theme";

// Custom filled home icon (Tabler doesn't have IconHomeFilled)
function HomeFilled({
	size = 24,
	color = "currentColor",
}: {
	size?: number;
	color?: string;
}) {
	return (
		<svg
			xmlns="http://www.w3.org/2000/svg"
			width={size}
			height={size}
			viewBox="0 0 24 24"
			fill={color}
			stroke="none"
		>
			<path d="M12.707 2.293a1 1 0 0 0-1.414 0l-7 7A1 1 0 0 0 4 10.414V19a2 2 0 0 0 2 2h3a1 1 0 0 0 1-1v-4a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v4a1 1 0 0 0 1 1h3a2 2 0 0 0 2-2v-8.586a1 1 0 0 0-.293-.707l-7-7z" />
		</svg>
	);
}

export interface NavItem {
	icon: typeof IconHome;
	filledIcon?: typeof IconHome;
	labelKey: string;
	path: string;
	badgeKey: "favoritesCount" | "unreadCount" | null;
}

interface NavTabProps {
	item: NavItem;
	isActive: boolean;
	badgeValue: number;
	onClick: () => void;
	t: (key: string) => string;
	iconOnly?: boolean;
}

export const NavTab = forwardRef<HTMLButtonElement, NavTabProps>(
	function NavTab({ item, isActive, badgeValue, onClick, t, iconOnly }, ref) {
		return (
			<UnstyledButton
				ref={ref}
				onClick={onClick}
				style={{
					display: "flex",
					flexDirection: "column",
					alignItems: "center",
					justifyContent: "center",
					padding: "4px 0",
					borderRadius: radii.md,
					backgroundColor: "transparent",
					transition: transitions.spring,
					flex: 1,
					position: "relative",
				}}
			>
				<Box style={{ position: "relative" }}>
					{item.labelKey === "nav.home" ? (
						<HomeFilled size={24} color={isActive ? "#228be6" : "#2C3E50"} />
					) : item.filledIcon ? (
						<item.filledIcon
							size={24}
							style={{
								color: isActive ? "#228be6" : "#2C3E50",
								transition: transitions.spring,
							}}
						/>
					) : (
						<item.icon
							size={24}
							stroke={2}
							color={isActive ? "#228be6" : "#2C3E50"}
							style={{ transition: transitions.spring }}
						/>
					)}
					{badgeValue > 0 && (
						<Box
							style={{
								position: "absolute",
								top: -3,
								right: -6,
								minWidth: badgeValue > 9 ? 16 : 8,
								height: badgeValue > 9 ? 16 : 8,
								borderRadius: 8,
								backgroundColor: "#ff6b6b",
								border: "2px solid white",
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								padding: badgeValue > 9 ? "0 4px" : 0,
							}}
						>
							{badgeValue > 9 && (
								<Text
									style={{
										fontSize: 9,
										fontWeight: 700,
										color: "white",
										lineHeight: 1,
									}}
								>
									{badgeValue > 99 ? "99" : badgeValue}
								</Text>
							)}
						</Box>
					)}
				</Box>
				{!iconOnly && (
					<Text
						mt={2}
						style={{
							fontSize: 11,
							fontWeight: isActive ? 700 : 500,
							color: isActive ? "#228be6" : "#2C3E50",
							transition: "all 0.2s ease",
							whiteSpace: "nowrap",
							lineHeight: 1.2,
						}}
					>
						{t(item.labelKey)}
					</Text>
				)}
			</UnstyledButton>
		);
	},
);
