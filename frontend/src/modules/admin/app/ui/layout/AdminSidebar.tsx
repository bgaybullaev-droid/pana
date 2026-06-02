import {
	Box,
	Drawer,
	ScrollArea,
	Text,
	Tooltip,
	UnstyledButton,
} from "@mantine/core";
import {
	IconLayoutSidebarLeftCollapse,
	IconLayoutSidebarLeftExpand,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { useAdminNav, type ResolvedNavItem } from "./useAdminNav";
import { AdminNavItem, type NavMode } from "./AdminNavItem";

interface AdminSidebarProps {
	/** Desktop (>= 992px) shows the persistent sidebar; otherwise the mobile drawer. */
	isDesktop: boolean;
	/** Desktop rail (icons only) vs full (icons + labels). */
	collapsed: boolean;
	onToggleCollapsed: () => void;
	/** Mobile drawer state. */
	drawerOpened: boolean;
	onCloseDrawer: () => void;
}

/**
 * Admin navigation surface. Renders either the persistent left sidebar
 * (desktop, collapsible full <-> rail) or the slide-in drawer (mobile).
 * Both reuse the same resolved items from `useAdminNav` and the same
 * `AdminNavItem` presentation.
 */
export function AdminSidebar({
	isDesktop,
	collapsed,
	onToggleCollapsed,
	drawerOpened,
	onCloseDrawer,
}: AdminSidebarProps) {
	const { items, navigate } = useAdminNav();
	const { t } = useTranslation("admin");

	const navList = (mode: NavMode, onItemClick: (path: string) => void) => (
		<Box
			component="nav"
			aria-label={t("header.title")}
			style={{ display: "flex", flexDirection: "column", gap: 4, padding: 8 }}
		>
			{items.map((item: ResolvedNavItem) => (
				<AdminNavItem
					key={item.path}
					item={item}
					mode={mode}
					onClick={() => onItemClick(item.path)}
				/>
			))}
		</Box>
	);

	if (isDesktop) {
		const toggleLabel = collapsed
			? t("nav.expandSidebar")
			: t("nav.collapseSidebar");

		return (
			<Box
				component="aside"
				className={`admin-sidebar${collapsed ? " admin-sidebar--rail" : ""}`}
			>
				<Box className="admin-sidebar-header">
					{!collapsed && (
						<Text className="admin-sidebar-brand">{t("header.brand")}</Text>
					)}
					<Tooltip label={toggleLabel} position="right" withArrow>
						<UnstyledButton
							onClick={onToggleCollapsed}
							aria-label={toggleLabel}
							className="admin-sidebar-toggle"
						>
							{collapsed ? (
								<IconLayoutSidebarLeftExpand size={20} />
							) : (
								<IconLayoutSidebarLeftCollapse size={20} />
							)}
						</UnstyledButton>
					</Tooltip>
				</Box>

				<ScrollArea type="hover" style={{ flex: 1, minHeight: 0 }}>
					{navList(collapsed ? "rail" : "full", navigate)}
				</ScrollArea>
			</Box>
		);
	}

	return (
		<Drawer
			opened={drawerOpened}
			onClose={onCloseDrawer}
			position="left"
			size={260}
			zIndex={10001}
			title={
				<Text fw={700} className="admin-sidebar-brand">
					{t("header.brand")}
				</Text>
			}
			scrollAreaComponent={ScrollArea.Autosize}
			classNames={{ body: "admin-sidebar-drawer-body" }}
		>
			{navList("drawer", (path) => {
				navigate(path);
				onCloseDrawer();
			})}
		</Drawer>
	);
}
