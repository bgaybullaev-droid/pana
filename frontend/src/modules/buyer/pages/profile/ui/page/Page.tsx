import { useEffect, useState } from "react";
import { useAuth } from "@app/providers/useAuth";
import { useTelegram } from "@app/providers/useTelegram";
import { useTranslation } from "react-i18next";
import { useUnit } from "effector-react";
import { notificationsApi } from "@shared/api/notifications";
import {
	Stack,
	Avatar,
	Text,
	Group,
	Button,
	Switch,
	Box,
	UnstyledButton,
} from "@mantine/core";
import {
	IconUser,
	IconBell,
	IconLogout,
	IconBriefcase,
	IconArrowRight,
	IconLanguage,
	IconPackage,
	IconPlus,
	IconChartBar,
	IconArrowLeft,
	IconPhone,
	IconCoin,
} from "@tabler/icons-react";
import { useNavigate } from "react-router-dom";
import {
	$sellerStats,
	$profileCheckComplete,
	fetchSellerProfile,
} from "@modules/seller/shared/state";
import { UnauthScreen } from "@shared/ui/UnauthScreen";
import { ProfileMenuItem } from "@shared/ui/ProfileMenuItem";
import { LanguageSwitcher } from "@shared/ui/LanguageSwitcher";
import { ActionIcon } from "@mantine/core";
import { shadows, gradients, radii, surface } from "@app/styles/theme";

function Page() {
	const { t } = useTranslation("buyer");
	const { user, isAuthenticated, logout } = useAuth();
	const { webApp } = useTelegram();
	const navigate = useNavigate();
	const [sellerStats, profileCheckDone] = useUnit([
		$sellerStats,
		$profileCheckComplete,
	]);

	// Push notifications state
	const [pushEnabled, setPushEnabled] = useState(true);
	const [pushLoading, setPushLoading] = useState(true);

	// Fetch seller profile if user is a seller and we haven't checked yet
	useEffect(() => {
		if (user?.is_seller && !profileCheckDone) {
			fetchSellerProfile();
		}
	}, [user, profileCheckDone]);

	// Fetch notification preferences
	useEffect(() => {
		if (!isAuthenticated) return;
		notificationsApi
			.getPreferences()
			.then((prefs) => setPushEnabled(prefs.enabled))
			.catch(() => {})
			.finally(() => setPushLoading(false));
	}, [isAuthenticated]);

	if (!isAuthenticated) {
		return (
			<UnauthScreen
				icon={IconUser}
				title={t("profile.title")}
				subtitle={t("profile.loginSubtitle")}
				loginPrompt={t("profile.loginPrompt")}
				loginLabel={t("common.login")}
				onLogin={() => navigate("/auth")}
				onBack={() => navigate(-1)}
			>
				<Box px="md" mt="md">
					<Box
						style={{
							backgroundColor: surface.card,
							borderRadius: radii.lg,
							padding: "12px 16px",
							boxShadow: shadows.md,
						}}
					>
						<Group justify="space-between">
							<Group gap={12}>
								<Box
									style={{
										width: 36,
										height: 36,
										borderRadius: radii.md,
										backgroundColor: "#e7f5ff",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
									}}
								>
									<IconLanguage size={18} color="#228be6" stroke={2} />
								</Box>
								<Text fw={500} size="sm">
									{t("profile.language")}
								</Text>
							</Group>
							<LanguageSwitcher variant="light" />
						</Group>
					</Box>
				</Box>
			</UnauthScreen>
		);
	}

	const handleLogout = () => {
		const message = t("profile.logoutConfirm");
		try {
			webApp?.showConfirm(message, (confirmed: boolean) => {
				if (confirmed) {
					logout();
				}
			});
		} catch {
			if (window.confirm(message)) {
				logout();
			}
		}
	};

	// Seller section menu items (only shown if user.is_seller)
	const sellerMenuItems = [
		{
			icon: IconPackage,
			label: `${t("profile.myListings")}${sellerStats ? ` (${sellerStats.totalListings})` : ""}`,
			color: "#228be6",
			bg: "#e7f5ff",
			onClick: () => navigate("/seller/listings"),
		},
		{
			icon: IconPlus,
			label: t("profile.createListing"),
			color: "#40c057",
			bg: "#ebfbee",
			onClick: () => navigate("/seller/create"),
		},
		{
			icon: IconChartBar,
			label: t("profile.sellerDashboard"),
			color: "#7950f2",
			bg: "#f3f0ff",
			onClick: () => navigate("/seller/dashboard"),
		},
		{
			icon: IconPhone,
			label: t("nav.phones", { ns: "seller" }),
			color: "#0891b2",
			bg: "#cffafe",
			onClick: () => navigate("/seller/phones"),
		},
		{
			icon: IconCoin,
			label: t("nav.tariffs", { ns: "seller" }),
			color: "#f59e0b",
			bg: "#fef3c7",
			onClick: () => navigate("/seller/tariffs"),
		},
		{
			icon: IconBell,
			label: t("profile.menuNotifications"),
			color: "#228be6",
			bg: "#e7f5ff",
			onClick: () => navigate("/notifications"),
		},
	];

	return (
		<Box mih="100vh" style={{ backgroundColor: surface.page }}>
			{/* Gradient header */}
			<Box
				style={{
					background: gradients.header,
					padding: "40px 20px 60px",
					textAlign: "center",
					position: "relative",
					overflow: "hidden",
				}}
			>
				{/* Back button */}
				<ActionIcon
					variant="transparent"
					size={56}
					onClick={() => navigate(-1)}
					style={{
						position: "absolute",
						top: 12,
						left: 12,
						zIndex: 2,
						backgroundColor: "rgba(255, 255, 255, 0.65)",
						backdropFilter: "blur(20px) saturate(180%)",
						WebkitBackdropFilter: "blur(20px) saturate(180%)",
						border: "1px solid rgba(255, 255, 255, 0.5)",
						boxShadow: shadows.md,
						borderRadius: radii.full,
					}}
				>
					<IconArrowLeft size={24} color="#868e96" />
				</ActionIcon>

				{/* Decorative circles */}

				<Box
					style={{
						position: "absolute",
						top: -30,
						right: -30,
						width: 120,
						height: 120,
						borderRadius: radii.full,
						backgroundColor: "rgba(255,255,255,0.08)",
					}}
				/>
				<Box
					style={{
						position: "absolute",
						bottom: 10,
						left: -20,
						width: 80,
						height: 80,
						borderRadius: radii.full,
						backgroundColor: "rgba(255,255,255,0.06)",
					}}
				/>

				{/* Avatar */}
				<Box
					style={{
						display: "flex",
						justifyContent: "center",
						marginBottom: 12,
					}}
				>
					<Box
						style={{
							width: 76,
							height: 76,
							borderRadius: radii.full,
							border: "3px solid rgba(255,255,255,0.5)",
							boxShadow: shadows.lg,
							display: "flex",
							alignItems: "center",
							justifyContent: "center",
						}}
					>
						<Avatar
							size={70}
							color="blue.7"
							radius="xl"
							style={{ fontSize: 28 }}
						>
							{user?.first_name?.[0] || <IconUser size={28} />}
						</Avatar>
					</Box>
				</Box>

				<Text size="lg" fw={700} c="white">
					{user?.first_name} {user?.last_name}
				</Text>
				{user?.username && (
					<Text size="sm" c="rgba(255,255,255,0.75)" mt={2}>
						@{user.username}
					</Text>
				)}
			</Box>

			{/* Content */}
			<Box px="md" style={{ marginTop: -30, position: "relative", zIndex: 1 }}>
				<Stack gap={12}>
					{/* Become seller CTA (non-sellers only) */}
					{!user?.is_seller && (
						<UnstyledButton
							onClick={() => navigate("/become-seller")}
							style={{ display: "block" }}
						>
							<Box
								style={{
									background: gradients.orange,
									borderRadius: radii.lg,
									padding: "16px 18px",
									boxShadow: shadows.accentOrange,
								}}
							>
								<Group justify="space-between" wrap="nowrap">
									<Group gap={12} wrap="nowrap">
										<Box
											style={{
												width: 44,
												height: 44,
												borderRadius: radii.md,
												backgroundColor: "rgba(255,255,255,0.2)",
												display: "flex",
												alignItems: "center",
												justifyContent: "center",
											}}
										>
											<IconBriefcase size={22} color="white" />
										</Box>
										<Box>
											<Text fw={700} c="white" size="sm">
												{t("profile.becomeSeller")}
											</Text>
											<Text size="xs" c="rgba(255,255,255,0.85)">
												{t("profile.becomeSellerDescription")}
											</Text>
										</Box>
									</Group>
									<IconArrowRight size={20} color="white" />
								</Group>
							</Box>
						</UnstyledButton>
					)}

					{/* C1 V2.0: pricing info available to non-sellers too —
					    tariffs are visible from day 1 per spec. */}
					{!user?.is_seller && (
						<UnstyledButton
							onClick={() => navigate("/seller/tariffs")}
							style={{ display: "block" }}
						>
							<Box
								style={{
									background:
										"linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)",
									border: "1px solid #fcd34d",
									borderRadius: radii.lg,
									padding: "14px 16px",
									boxShadow: shadows.sm,
								}}
							>
								<Group justify="space-between" wrap="nowrap">
									<Group gap={12} wrap="nowrap">
										<Box
											style={{
												width: 40,
												height: 40,
												borderRadius: radii.md,
												backgroundColor: "rgba(255,255,255,0.7)",
												display: "flex",
												alignItems: "center",
												justifyContent: "center",
											}}
										>
											<IconCoin size={20} color="#b45309" />
										</Box>
										<Box>
											<Text fw={700} c="#78350f" size="sm">
												{t("nav.tariffs", { ns: "seller" })}
											</Text>
											<Text size="xs" c="#92400e">
												{t("tariffs.heroBanner", { ns: "seller" })}
											</Text>
										</Box>
									</Group>
									<IconArrowRight size={20} color="#92400e" />
								</Group>
							</Box>
						</UnstyledButton>
					)}

					{/* Seller section (sellers only) */}
					{user?.is_seller && (
						<Box
							style={{
								backgroundColor: surface.card,
								borderRadius: radii.lg,
								boxShadow: shadows.md,
								overflow: "hidden",
							}}
						>
							{sellerMenuItems.map((item, index) => (
								<ProfileMenuItem
									key={item.label}
									icon={item.icon}
									label={item.label}
									color={item.color}
									bg={item.bg}
									onClick={item.onClick}
									showBorder={index < sellerMenuItems.length - 1}
								/>
							))}
						</Box>
					)}

					{/* Notifications toggle */}
					<Box
						style={{
							backgroundColor: surface.card,
							borderRadius: radii.lg,
							padding: "12px 16px",
							boxShadow: shadows.md,
						}}
					>
						<Group justify="space-between">
							<Group gap={12}>
								<Box
									style={{
										width: 36,
										height: 36,
										borderRadius: radii.md,
										backgroundColor: "#f3f0ff",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
									}}
								>
									<IconBell size={18} color="#7950f2" stroke={2} />
								</Box>
								<Text fw={500} size="sm">
									{t("profile.pushNotifications")}
								</Text>
							</Group>
							<Switch
								checked={pushEnabled}
								disabled={pushLoading}
								onChange={(e) => {
									const checked = e.currentTarget.checked;
									setPushEnabled(checked);
									notificationsApi
										.updatePreferences({ enabled: checked })
										.catch(() => setPushEnabled(!checked));
								}}
								size="md"
							/>
						</Group>
					</Box>

					{/* Language switcher */}
					<Box
						style={{
							backgroundColor: surface.card,
							borderRadius: radii.lg,
							padding: "12px 16px",
							boxShadow: shadows.md,
						}}
					>
						<Group justify="space-between">
							<Group gap={12}>
								<Box
									style={{
										width: 36,
										height: 36,
										borderRadius: radii.md,
										backgroundColor: "#e7f5ff",
										display: "flex",
										alignItems: "center",
										justifyContent: "center",
									}}
								>
									<IconLanguage size={18} color="#228be6" stroke={2} />
								</Box>
								<Text fw={500} size="sm">
									{t("profile.language")}
								</Text>
							</Group>
							<LanguageSwitcher variant="light" />
						</Group>
					</Box>

					{/* Logout */}
					<Box ta="center" mt={8}>
						<Button
							variant="subtle"
							color="red"
							size="sm"
							leftSection={<IconLogout size={16} />}
							onClick={handleLogout}
							style={{ fontWeight: 500 }}
						>
							{t("profile.logout")}
						</Button>
					</Box>

					{/* Version */}
					<Text ta="center" size="xs" c="dimmed" pb="md">
						{t("profile.version")}
					</Text>
				</Stack>
			</Box>
		</Box>
	);
}

export const Profile = {
	route: "/profile",
	Page,
};
