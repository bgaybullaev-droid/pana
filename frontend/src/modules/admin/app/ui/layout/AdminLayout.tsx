import { Outlet, useNavigate, Navigate } from "react-router-dom";
import { Box, Text, Group, Burger } from "@mantine/core";
import { useDisclosure, useLocalStorage, useMediaQuery } from "@mantine/hooks";
import { PageBar } from "@shared/ui/PageBar";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@app/providers/useAuth";
import { fetchDashboardStats } from "@modules/admin/shared/state";
import { LanguageSwitcher } from "@shared/ui/LanguageSwitcher";
import { AdminSidebar } from "./AdminSidebar";
import "@modules/admin/shared/ui/admin.css";

export function AdminLayout() {
	const navigate = useNavigate();
	const { user, isAuthenticated, isLoading } = useAuth();
	const { t } = useTranslation("admin");

	useEffect(() => {
		document.title = "Uchar Admin";
		return () => {
			document.title = "Ucharmarket - Вся недвижимость Узбекистана";
		};
	}, []);

	// Responsive + persisted UI state (declared before early returns for Rules of Hooks).
	// Default `true` keeps the desktop sidebar on first paint (no flash); this is a Vite SPA.
	const isDesktop = useMediaQuery("(min-width: 992px)", true) ?? true;
	const [collapsed, setCollapsed] = useLocalStorage<boolean>({
		key: "admin:sidebarCollapsed",
		defaultValue: false,
		getInitialValueInEffect: false,
	});
	const [drawerOpened, { open: openDrawer, close: closeDrawer }] =
		useDisclosure(false);

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
				flexDirection: "row",
				height: "100%",
				width: "100%",
				background: "linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%)",
			}}
		>
			{/* Left navigation: persistent sidebar (desktop) or slide-in drawer (mobile) */}
			<AdminSidebar
				isDesktop={isDesktop}
				collapsed={collapsed}
				onToggleCollapsed={() => setCollapsed((c) => !c)}
				drawerOpened={drawerOpened}
				onCloseDrawer={closeDrawer}
			/>

			{/* Right column: header + scrollable content */}
			<Box
				style={{
					display: "flex",
					flexDirection: "column",
					flex: 1,
					minWidth: 0,
					height: "100%",
				}}
			>
				<PageBar
					title={t("header.title")}
					onBack={() => navigate("/")}
					leftSlot={
						isDesktop ? undefined : (
							<Burger
								opened={drawerOpened}
								onClick={openDrawer}
								aria-label={t("nav.openMenu")}
								size="sm"
							/>
						)
					}
					actions={
						<Group gap={8}>
							<LanguageSwitcher />
							<Text size="xs" fw={600} c="dimmed">
								{firstName}
							</Text>
						</Group>
					}
				/>

				<Box
					style={{ flex: 1, overflow: "auto" }}
					className="admin-page-bg hide-scrollbar"
				>
					<Box style={{ maxWidth: 980, margin: "0 auto", width: "100%" }}>
						<Outlet />
					</Box>
				</Box>
			</Box>
		</Box>
	);
}
