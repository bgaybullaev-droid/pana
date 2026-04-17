import { Outlet, useLocation, useNavigate, Navigate } from "react-router-dom";
import { Box, UnstyledButton, Text, Group } from "@mantine/core";
import { PageBar } from "@shared/ui/PageBar";
import {
	IconLayoutDashboard,
	IconUsers,
	IconList,
	IconWorldSearch,
	IconServerCog,
	IconHistory,
} from "@tabler/icons-react";
import { useUnit } from "effector-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@app/providers/useAuth";
import {
	$dashboardStats,
	fetchDashboardStats,
} from "@modules/admin/shared/state";
import { LanguageSwitcher } from "@shared/ui/LanguageSwitcher";
import "@modules/admin/shared/ui/admin.css";

interface NavItem {
	icon: typeof IconLayoutDashboard;
	labelKey: string;
	path: string;
	badgeKey?: "pending_users" | "pending_listings";
}

const NAV_ITEMS: NavItem[] = [
	{
		icon: IconLayoutDashboard,
		labelKey: "nav.dashboard",
		path: "/admin",
	},
	{
		icon: IconUsers,
		labelKey: "nav.users",
		path: "/admin/users",
		badgeKey: "pending_users",
	},
	{
		icon: IconList,
		labelKey: "nav.listings",
		path: "/admin/listings",
		badgeKey: "pending_listings",
	},
	{
		icon: IconWorldSearch,
		labelKey: "nav.crawled",
		path: "/admin/crawled",
	},
	{
		icon: IconServerCog,
		labelKey: "nav.meiliOps",
		path: "/admin/ops/meili",
	},
	{
		icon: IconHistory,
		labelKey: "nav.auditLog",
		path: "/admin/audit",
	},
];

export function AdminLayout() {
	const location = useLocation();
	const navigate = useNavigate();
	const { user, isAuthenticated, isLoading } = useAuth();
	const [stats] = useUnit([$dashboardStats]);
	const { t } = useTranslation("admin");

	// Fetch dashboard stats on mount (must be before early returns for Rules of Hooks)
	useEffect(() => {
		if (isAuthenticated && user?.role === "admin") {
			fetchDashboardStats();
		}
	}, [isAuthenticated, user?.role]);

	// Show loading while checking auth
	if (isLoading) {
		return null;
	}

	// Redirect to admin login if not authenticated or not admin
	if (!isAuthenticated || user?.role !== "admin") {
		return <Navigate to="/admin/login" replace />;
	}

	const firstName = user?.first_name || "Admin";

	return (
		<Box
			style={{
				display: "flex",
				flexDirection: "column",
				height: "93%",
				width: "100%",
				background: "linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)",
			}}
		>
			{/* Header */}
			<PageBar
				title={t("header.title")}
				onBack={() => navigate("/")}
				actions={
					<Group gap={8}>
						<LanguageSwitcher />
						<Text size="xs" fw={600} c="dimmed">
							{firstName}
						</Text>
					</Group>
				}
			/>

			{/* Main content */}
			<Box
				style={{
					flex: 1,
					overflow: "auto",
					paddingBottom: "calc(72px + env(safe-area-inset-bottom, 0px))",
				}}
				className="admin-page-bg hide-scrollbar"
			>
				<Box style={{ maxWidth: 980, margin: "0 auto", width: "100%" }}>
					<Outlet />
				</Box>
			</Box>

			{/* Bottom navigation */}
			<Box
				component="nav"
				className="admin-bottom-nav"
				style={{
					position: "fixed",
					bottom: 0,
					left: 0,
					right: 0,
					paddingBottom: "env(safe-area-inset-bottom, 0px)",
					zIndex: 100,
				}}
			>
				<Box
					style={{
						display: "flex",
						justifyContent: "space-around",
						padding: "6px 8px",
						gap: 4,
					}}
				>
					{NAV_ITEMS.map((item) => {
						const isActive =
							item.path === "/admin"
								? location.pathname === "/admin"
								: location.pathname.startsWith(item.path);
						const badgeCount =
							item.badgeKey && stats ? stats[item.badgeKey] : 0;
						const Icon = item.icon;

						return (
							<UnstyledButton
								key={item.path}
								onClick={() => navigate(item.path)}
								className={`admin-nav-item ${isActive ? "admin-nav-item--active" : ""}`}
							>
								<Box style={{ position: "relative" }}>
									<Icon
										size={22}
										color={isActive ? "#4f46e5" : "#94a3b8"}
										stroke={isActive ? 2 : 1.5}
									/>
									{!!badgeCount && badgeCount > 0 && (
										<Box className="admin-nav-badge-wrap">
											<Box className="admin-nav-badge-ping" />
											<Box
												style={{
													position: "relative",
													background: "#ef4444",
													color: "white",
													fontSize: 9,
													fontWeight: 700,
													borderRadius: 9999,
													minWidth: 16,
													height: 16,
													display: "flex",
													alignItems: "center",
													justifyContent: "center",
													padding: "0 4px",
												}}
											>
												{badgeCount > 99 ? "99+" : badgeCount}
											</Box>
										</Box>
									)}
								</Box>
								<Text
									size="xs"
									mt={2}
									fw={isActive ? 700 : 500}
									style={{
										color: isActive ? "#4f46e5" : "#94a3b8",
										fontSize: 11,
										transition: "color 0.2s ease",
									}}
								>
									{t(item.labelKey)}
								</Text>
								{isActive && <Box className="admin-nav-dot" />}
							</UnstyledButton>
						);
					})}
				</Box>
			</Box>
		</Box>
	);
}
