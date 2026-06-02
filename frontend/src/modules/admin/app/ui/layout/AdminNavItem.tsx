import { Box, Text, Tooltip, UnstyledButton } from "@mantine/core";
import type { ResolvedNavItem } from "./useAdminNav";

export type NavMode = "full" | "rail" | "drawer";

interface AdminNavItemProps {
	item: ResolvedNavItem;
	mode: NavMode;
	onClick: () => void;
}

/**
 * One navigation row, rendered in three modes:
 *  - full   (desktop expanded): icon + label, number badge at the row end
 *  - rail   (desktop collapsed): centered icon only, dot badge, label in a tooltip
 *  - drawer (mobile): same as full
 */
export function AdminNavItem({ item, mode, onClick }: AdminNavItemProps) {
	const Icon = item.icon;
	const isRail = mode === "rail";
	const badge =
		item.badgeCount > 0 ? (item.badgeCount > 99 ? "99+" : item.badgeCount) : null;

	const button = (
		<UnstyledButton
			onClick={onClick}
			aria-current={item.isActive ? "page" : undefined}
			aria-label={isRail ? item.label : undefined}
			className={`admin-sidebar-item${
				item.isActive ? " admin-sidebar-item--active" : ""
			}${isRail ? " admin-sidebar-item--rail" : ""}`}
		>
			<Box className="admin-sidebar-item-icon">
				<Icon
					size={22}
					color={item.isActive ? "#4f46e5" : "#64748b"}
					stroke={item.isActive ? 2 : 1.6}
				/>
				{badge && isRail && (
					<Box className="admin-sidebar-badge admin-sidebar-badge--dot" />
				)}
			</Box>

			{!isRail && (
				<Text className="admin-sidebar-item-label" fw={item.isActive ? 700 : 500}>
					{item.label}
				</Text>
			)}

			{!isRail && badge && <Box className="admin-sidebar-badge">{badge}</Box>}
		</UnstyledButton>
	);

	return isRail ? (
		<Tooltip label={item.label} position="right" withArrow openDelay={150}>
			{button}
		</Tooltip>
	) : (
		button
	);
}
