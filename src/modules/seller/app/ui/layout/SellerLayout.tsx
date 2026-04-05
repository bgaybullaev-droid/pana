import { Outlet, useLocation, useNavigate } from "react-router-dom";
import { SellerLoginGate } from "./SellerLoginGate";
import {
	Box,
	UnstyledButton,
	Text,
	Group,
	LoadingOverlay,
	ActionIcon,
} from "@mantine/core";
import {
	IconLayoutDashboard,
	IconList,
	IconPlus,
	IconUser,
	IconLogout,
} from "@tabler/icons-react";
import { PageBar } from "@shared/ui/PageBar";
import { useEffect } from "react";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@app/providers/useAuth";
import {
	$sellerProfile,
	$isLoadingProfile,
	$profileCheckComplete,
	fetchSellerProfile,
} from "@modules/seller/shared/state";
import { LanguageSwitcher } from "@shared/ui/LanguageSwitcher";

interface NavItem {
	icon: typeof IconLayoutDashboard;
	labelKey: string;
	path: string;
}

const NAV_ITEMS: NavItem[] = [
	{
		icon: IconLayoutDashboard,
		labelKey: "nav.dashboard",
		path: "/seller/dashboard",
	},
	{ icon: IconList, labelKey: "nav.listings", path: "/seller/listings" },
	{ icon: IconPlus, labelKey: "nav.create", path: "/seller/listings/create" },
	{ icon: IconUser, labelKey: "nav.profile", path: "/seller/profile" },
];

export function SellerLayout() {
	const location = useLocation();
	const navigate = useNavigate();
	const { t } = useTranslation("seller");
	const { user, isLoading: isAuthLoading, logout } = useAuth();
	const [sellerProfile, isLoadingProfile, profileCheckDone] = useUnit([
		$sellerProfile,
		$isLoadingProfile,
		$profileCheckComplete,
	]);

	useEffect(() => {
		if (user && !sellerProfile && !isLoadingProfile && !profileCheckDone) {
			fetchSellerProfile();
		}
	}, [user, sellerProfile, isLoadingProfile, profileCheckDone]);

	if (isAuthLoading) {
		return (
			<Box
				style={{
					display: "flex",
					height: "100%",
					justifyContent: "center",
					alignItems: "center",
				}}
			>
				<LoadingOverlay visible />
			</Box>
		);
	}

	if (!user) {
		return <SellerLoginGate />;
	}

	if (!profileCheckDone || isLoadingProfile) {
		return (
			<Box
				style={{
					display: "flex",
					height: "100%",
					justifyContent: "center",
					alignItems: "center",
				}}
			>
				<LoadingOverlay visible />
			</Box>
		);
	}

	if (!sellerProfile) {
		// Show OTP login — user can auth directly via phone + Telegram OTP
		// This also creates their seller profile automatically on verify
		return <SellerLoginGate />;
	}

	return (
		<Box
			style={{
				display: "flex",
				flexDirection: "column",
				height: "100%",
				width: "100%",
			}}
		>
			{/* Header */}
			<PageBar
				title={t("header.sellerPanel")}
				onBack={() =>
					navigate(
						location.pathname === "/seller/dashboard"
							? "/"
							: "/seller/dashboard",
					)
				}
				actions={
					<Group gap="xs">
						<LanguageSwitcher />
						<ActionIcon
							variant="subtle"
							color="gray"
							onClick={logout}
							title={t("header.logout")}
							style={{ borderRadius: 8 }}
						>
							<IconLogout size={20} />
						</ActionIcon>
					</Group>
				}
			/>

			{/* Main content area */}
			<Box
				style={{
					flex: 1,
					overflow: "auto",
					paddingBottom: "calc(68px + env(safe-area-inset-bottom, 0px))",
				}}
				className="hide-scrollbar"
			>
				<Box style={{ maxWidth: 980, margin: "0 auto", width: "100%" }}>
					<Outlet />
				</Box>
			</Box>

			{/* Glassmorphic Bottom Navigation */}
			<Box
				component="nav"
				style={{
					position: "fixed",
					bottom: 0,
					left: 0,
					right: 0,
					backgroundColor: "rgba(255, 255, 255, 0.92)",
					backdropFilter: "blur(20px)",
					WebkitBackdropFilter: "blur(20px)",
					borderTop: "1px solid rgba(0,0,0,0.06)",
					paddingBottom: "env(safe-area-inset-bottom, 0px)",
					zIndex: 1000,
				}}
			>
				<Box
					style={{
						display: "flex",
						justifyContent: "space-around",
						padding: "8px 0 4px",
					}}
				>
					{NAV_ITEMS.map((item) => {
						const isActive = location.pathname === item.path;

						return (
							<UnstyledButton
								key={item.path}
								onClick={() => navigate(item.path)}
								style={{
									display: "flex",
									flexDirection: "column",
									alignItems: "center",
									padding: "4px 12px",
									transition: "transform 0.2s ease",
									transform: isActive ? "scale(1.05)" : "scale(1)",
								}}
							>
								<item.icon
									size={24}
									color={
										isActive
											? "var(--mantine-color-blue-6)"
											: "var(--mantine-color-gray-5)"
									}
									stroke={isActive ? 2 : 1.5}
								/>
								{/* Active indicator dot */}
								{isActive && (
									<Box
										style={{
											width: 4,
											height: 4,
											borderRadius: 2,
											backgroundColor: "var(--mantine-color-blue-6)",
											marginTop: 2,
										}}
									/>
								)}
								<Text
									size="xs"
									mt={isActive ? 0 : 2}
									c={isActive ? "blue.6" : "gray.5"}
									fw={isActive ? 700 : 400}
								>
									{t(item.labelKey)}
								</Text>
							</UnstyledButton>
						);
					})}
				</Box>
			</Box>
		</Box>
	);
}
