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
	IconArrowLeft,
	IconLogout,
} from "@tabler/icons-react";
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
import { gradients } from "@app/styles/theme";

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
			{/* Gradient Header */}
			<Box
				style={{
					background: gradients.primary,
					padding: "12px 16px",
					boxShadow: "0 2px 8px rgba(34,139,230,0.15)",
					borderRadius: "0 0 16px 16px",
				}}
			>
				<Group justify="space-between">
					<Group gap="xs">
						<UnstyledButton
							onClick={() => {
								if (location.pathname === "/seller/dashboard") {
									navigate("/");
								} else {
									navigate("/seller/dashboard");
								}
							}}
							style={{
								width: 32,
								height: 32,
								borderRadius: 8,
								display: "flex",
								alignItems: "center",
								justifyContent: "center",
								transition: "background 0.2s ease",
							}}
						>
							<IconArrowLeft size={20} color="white" />
						</UnstyledButton>
						<Text fw={600} c="white">
							{t("header.sellerPanel")}
						</Text>
					</Group>
					<Group gap="xs">
						<LanguageSwitcher />
						{sellerProfile?.company_name && (
							<Text size="sm" c="rgba(255,255,255,0.8)" truncate maw={120}>
								{sellerProfile.company_name}
							</Text>
						)}
						<ActionIcon
							variant="subtle"
							color="white"
							onClick={logout}
							title={t("header.logout")}
							style={{
								borderRadius: 8,
							}}
						>
							<IconLogout size={20} color="rgba(255,255,255,0.9)" />
						</ActionIcon>
					</Group>
				</Group>
			</Box>

			{/* Main content area */}
			<Box
				style={{
					flex: 1,
					overflow: "auto",
					paddingBottom: "calc(68px + env(safe-area-inset-bottom, 0px))",
				}}
				className="hide-scrollbar"
			>
				<Outlet />
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
