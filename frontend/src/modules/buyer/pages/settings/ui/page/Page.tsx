import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useUnit } from "effector-react";
import { useAuth } from "@app/providers/useAuth";
import { useTelegram } from "@app/providers/useTelegram";
import { updateLanguageFx } from "@shared/state/auth/model";
import {
	backendToFrontendLocale,
	frontendToBackendLanguage,
} from "@shared/i18n";
import { formatPhone } from "@shared/lib/formatPhone";
import { clearDraft } from "@modules/seller/feature/listing-form/ui/listingDraftStorage";
import {
	Box,
	Text,
	Drawer,
	Modal,
	Button,
	SimpleGrid,
	Card,
	Group,
	ThemeIcon,
	Skeleton,
	SegmentedControl,
	UnstyledButton,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import {
	IconClipboardList,
	IconWallet,
	IconBell,
	IconSparkles,
	IconWorld,
	IconInfoCircle,
	IconBuilding,
	IconHelpCircle,
	IconHeadphones,
	IconShare2,
	IconFileText,
	IconFileCheck,
	IconList,
	IconEye,
	IconPhone,
	IconHeart,
	IconSearch,
	IconDeviceMobile,
	IconCoin,
	IconBrandTelegram,
	IconGift,
	IconArrowRight,
	IconPlus,
} from "@tabler/icons-react";
import { UnauthScreen } from "@shared/ui/UnauthScreen";
import { RootPage } from "@shared/ui/RootPage";
import { IconUser } from "@tabler/icons-react";
import {
	$sellerStats,
	$isLoadingProfile,
	fetchSellerProfile,
} from "@modules/seller/shared/state";
import { ProfileCard } from "./ProfileCard";
import { shadows, radii } from "@app/styles/theme";
import { SectionCard } from "./SectionCard";
import { SettingsRow } from "./SettingsRow";
import { DestructiveBlock } from "./DestructiveBlock";

// Global style for row tap feedback
const TAP_STYLE = `
  .settings-row:active {
    background-color: #F5F5F7 !important;
  }
`;

function Page() {
	const { t, i18n } = useTranslation("buyer");
	const { user, isAuthenticated, logout } = useAuth();
	const { webApp } = useTelegram();
	const navigate = useNavigate();

	const [stats, isLoadingStats] = useUnit([$sellerStats, $isLoadingProfile]);
	const { t: ts } = useTranslation("seller");

	// Fetch seller profile for stats if user is a seller
	useEffect(() => {
		if (user?.is_seller) {
			fetchSellerProfile();
		}
	}, [user?.is_seller]);

	// Drawer / modal state
	const [soonOpened, soonHandlers] = useDisclosure(false);
	const [logoutOpened, logoutHandlers] = useDisclosure(false);
	const [deleteOpened, deleteHandlers] = useDisclosure(false);

	if (!isAuthenticated) {
		return (
			<UnauthScreen
				icon={IconUser}
				title={t("settings.title")}
				subtitle={t("settings.loginSubtitle")}
				loginPrompt={t("settings.loginPrompt")}
				loginLabel={t("common.login")}
				onLogin={() => navigate("/auth")}
				onBack={() => navigate(-1)}
			/>
		);
	}

	const userName =
		[user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
		user?.username ||
		"";
	const initials =
		(user?.first_name?.[0] || "") + (user?.last_name?.[0] || "") ||
		user?.username?.[0]?.toUpperCase() ||
		"U";
	const phone = user?.phone ? formatPhone(user?.phone) : "";

	const handleLogout = () => {
		logoutHandlers.close();
		try {
			webApp?.showConfirm(t("settings.logoutConfirm"), (confirmed: boolean) => {
				if (confirmed) logout();
			});
		} catch {
			logout();
		}
	};

	const handleDelete = () => {
		deleteHandlers.close();
		// TODO: implement account deletion API
	};

	const handleShare = async () => {
		const shareData = {
			title: "UcharMarket",
			text: t("settings.shareText"),
			url: "https://ucharmarket.uz",
		};
		try {
			if (navigator.share) {
				await navigator.share(shareData);
			}
		} catch {
			// User cancelled share
		}
	};

	return (
		<RootPage title={t("settings.title")}>
			<style>{TAP_STYLE}</style>

			{/* ─── Profile Card ─── */}
			<ProfileCard
				name={userName}
				phone={phone}
				avatarUrl={user?.avatar_url}
				initials={initials}
				onEdit={() => navigate("/edit-profile")}
				editLabel={t("settings.edit")}
			/>

			{/* ─── Stats (sellers only) ─── */}
			{user?.is_seller && (
				<Box mt={8} mb={8}>
					<Text fw={600} size="13px" c="dimmed" mb={8}>
						{ts("dashboard.statsToday")}
					</Text>
					<SimpleGrid cols={2} spacing={8}>
						{isLoadingStats ? (
							<>
								<Skeleton height={60} radius={radii.md} />
								<Skeleton height={60} radius={radii.md} />
								<Skeleton height={60} radius={radii.md} />
								<Skeleton height={60} radius={radii.md} />
							</>
						) : (
							<>
								<Card
									radius={radii.md}
									p="sm"
									style={{
										boxShadow: shadows.md,
										border: "1px solid #f1f5f9",
									}}
								>
									<Group wrap="nowrap" align="center" gap="sm">
										<ThemeIcon
											size={32}
											radius="md"
											color="blue"
											variant="light"
										>
											<IconList size={16} />
										</ThemeIcon>
										<Box>
											<Text fw={800} size="18px" c="dark.9" lh={1}>
												{stats?.totalListings ?? 0}
											</Text>
											<Text size="10px" fw={600} c="dimmed">
												{ts("dashboard.listings")}
											</Text>
										</Box>
									</Group>
								</Card>
								<Card
									radius={radii.md}
									p="sm"
									style={{
										boxShadow: shadows.md,
										border: "1px solid #f1f5f9",
									}}
								>
									<Group wrap="nowrap" align="center" gap="sm">
										<ThemeIcon
											size={32}
											radius="md"
											color="teal"
											variant="light"
										>
											<IconEye size={16} />
										</ThemeIcon>
										<Box>
											<Text fw={800} size="18px" c="dark.9" lh={1}>
												{stats?.totalViews ?? 0}
											</Text>
											<Text size="10px" fw={600} c="dimmed">
												{ts("dashboard.views")}
											</Text>
										</Box>
									</Group>
								</Card>
								<Card
									radius={radii.md}
									p="sm"
									style={{
										boxShadow: shadows.md,
										border: "1px solid #f1f5f9",
									}}
								>
									<Group wrap="nowrap" align="center" gap="sm">
										<ThemeIcon
											size={32}
											radius="md"
											color="orange"
											variant="light"
										>
											<IconPhone size={16} />
										</ThemeIcon>
										<Box>
											<Text fw={800} size="18px" c="dark.9" lh={1}>
												{stats?.totalContacts ?? 0}
											</Text>
											<Text size="10px" fw={600} c="dimmed">
												{ts("dashboard.contacts")}
											</Text>
										</Box>
									</Group>
								</Card>
								<Card
									radius={radii.md}
									p="sm"
									style={{
										boxShadow: shadows.md,
										border: "1px solid #f1f5f9",
									}}
								>
									<Group wrap="nowrap" align="center" gap="sm">
										<ThemeIcon
											size={32}
											radius="md"
											color="pink"
											variant="light"
										>
											<IconHeart size={16} />
										</ThemeIcon>
										<Box>
											<Text fw={800} size="18px" c="dark.9" lh={1}>
												{stats?.totalFavorites ?? 0}
											</Text>
											<Text size="10px" fw={600} c="dimmed">
												{ts("dashboard.favorites")}
											</Text>
										</Box>
									</Group>
								</Card>
							</>
						)}
					</SimpleGrid>
				</Box>
			)}


			{/* ─── Seller Tools ─── */}
			<SectionCard label={t("settings.sections.sellerTools")}>
				<Box px={8} pt={8} pb={4}>
					<UnstyledButton
						onClick={() => { clearDraft(); navigate("/seller/create"); }}
						style={{ display: "block", width: "100%" }}
					>
						<Card
							radius={radii.md}
							p="sm"
							style={{
								background: "#228be6",
								color: "white",
								border: "none",
								boxShadow: shadows.accent,
							}}
						>
							<Group wrap="nowrap" justify="space-between">
								<Group wrap="nowrap" gap="sm">
									<Box
										style={{
											width: 32,
											height: 32,
											borderRadius: radii.sm,
											background: "rgba(255,255,255,0.2)",
											display: "flex",
											alignItems: "center",
											justifyContent: "center",
										}}
									>
										<IconPlus size={18} color="white" />
									</Box>
									<Text fw={600} size="13px">
										{ts("dashboard.createListing")}
									</Text>
								</Group>
								<IconArrowRight size={16} opacity={0.7} color="white" />
							</Group>
						</Card>
					</UnstyledButton>
				</Box>
				<SettingsRow
					icon={IconClipboardList}
					label={t("settings.myListings")}
					onClick={() => navigate("/seller/listings")}
				/>
				<SettingsRow
					icon={IconSearch}
					label={ts("dashboard.found") || t("settings.found")}
					onClick={() => navigate("/seller/found")}
				/>
				<SettingsRow
					icon={IconBrandTelegram}
					label={ts("autopost.title")}
					onClick={() => navigate("/seller/autoposting")}
				/>
				<SettingsRow
					icon={IconDeviceMobile}
					label={ts("nav.phones")}
					onClick={() => navigate("/seller/phones")}
				/>
				<SettingsRow
					icon={IconWallet}
					label={t("settings.myBalance")}
					onClick={soonHandlers.open}
					variant="soon"
				/>
				<SettingsRow
					icon={IconCoin}
					label={ts("nav.tariffs")}
					onClick={() => navigate("/seller/tariffs")}
					rightValue={ts("tariffs.heroBanner")}
					showDivider={false}
				/>
			</SectionCard>

			{/* ─── Preferences ─── */}
			<SectionCard label={t("settings.sections.preferences")}>
				<SettingsRow
					icon={IconBell}
					label={t("settings.notifications")}
					onClick={() => navigate("/notification-settings")}
				/>
				<SettingsRow
					icon={IconSparkles}
					label={t("settings.recommendations")}
					onClick={() => navigate("/preferences")}
				/>
				<SettingsRow
					icon={IconWorld}
					label={t("settings.language")}
					onClick={() => {}}
					hideChevron
					rightElement={
						<Box onClick={(e) => e.stopPropagation()}>
							<SegmentedControl
								data={[
									{ label: "RU", value: "ru" },
									{ label: "UZ", value: "uz-latn" },
									{ label: "ЎЗ", value: "uz-cyrl" },
								]}
								value={(() => {
									const cur = backendToFrontendLocale(i18n.language);
									// Treat the ambiguous "uz" as "uz-latn" in the picker
									// so the Latin segment stays selected after auth-sync.
									return cur === "uz" ? "uz-latn" : cur;
								})()}
								onChange={(val) => {
									i18n.changeLanguage(val);
									localStorage.setItem("i18nextLng", val);
									if (isAuthenticated) {
										// Best-effort persist to backend; UI does not block
										// on the network call. updateLanguageFx.doneData
										// refreshes $user so subsequent reads see the
										// new value.
										updateLanguageFx(frontendToBackendLanguage(val)).catch(
											() => {
												/* swallow — local change already applied */
											},
										);
									}
								}}
								size="xs"
								radius="xl"
								styles={{
									root: {
										borderRadius: 9999,
										padding: 4,
									},
									indicator: {
										borderRadius: 9999,
									},
									label: {
										padding: "2px 12px",
										borderRadius: 9999,
									},
								}}
							/>
						</Box>
					}
					showDivider={false}
				/>
			</SectionCard>

			{/* ─── Bring Friends ─── */}
			<SectionCard label="Приведи друзей">
				<SettingsRow
					icon={IconGift}
					label={ts("nav.referrals")}
					onClick={() => navigate("/seller/referrals")}
				/>
				<SettingsRow
					icon={IconShare2}
					label={t("settings.shareWithFriend")}
					onClick={handleShare}
					showDivider={false}
				/>
			</SectionCard>

			{/* ─── About & Help ─── */}
			<SectionCard label={t("settings.sections.aboutHelp")}>
				<SettingsRow
					icon={IconInfoCircle}
					label={t("settings.about")}
					onClick={() => navigate("/about")}
				/>
				<SettingsRow
					icon={IconBuilding}
					label={t("settings.forRealtors")}
					onClick={() => navigate("/for-realtors")}
				/>
				<SettingsRow
					icon={IconHelpCircle}
					label={t("settings.faq")}
					onClick={() => navigate("/faq")}
				/>
				<SettingsRow
					icon={IconHeadphones}
					label={t("settings.support")}
					onClick={() => navigate("/support")}
					showDivider={false}
				/>
			</SectionCard>

			{/* ─── Legal ─── */}
			<SectionCard label={t("settings.sections.legal")}>
				<SettingsRow
					icon={IconFileText}
					label={t("settings.privacy")}
					onClick={() => navigate("/privacy")}
				/>
				<SettingsRow
					icon={IconFileCheck}
					label={t("settings.terms")}
					onClick={() => navigate("/terms")}
					showDivider={false}
				/>
			</SectionCard>

			{/* ─── Destructive Zone ─── */}
			<DestructiveBlock
				logoutLabel={t("settings.logout")}
				deleteLabel={t("settings.deleteAccount")}
				onLogout={logoutHandlers.open}
				onDelete={deleteHandlers.open}
			/>

			{/* ─── Version Footer ─── */}
			<Text
				ta="center"
				style={{
					fontSize: 12,
					fontWeight: 400,
					color: "#C7C7CC",
					marginTop: 20,
				}}
			>
				v1.0.0
			</Text>

			{/* ─── "Coming Soon" Bottom Sheet ─── */}
			<Drawer
				opened={soonOpened}
				onClose={soonHandlers.close}
				position="bottom"
				size="auto"
				withCloseButton={false}
				radius="16 16 0 0"
				padding="xl"
				styles={{
					body: { textAlign: "center", paddingBottom: 32 },
				}}
			>
				<Text
					style={{
						fontSize: 20,
						fontWeight: 600,
						color: "#1C1C1E",
						marginBottom: 8,
					}}
				>
					{t("settings.soonTitle")}
				</Text>
				<Text
					style={{
						fontSize: 15,
						color: "#8E8E93",
						marginBottom: 24,
					}}
				>
					{t("settings.soonMessage")}
				</Text>
				<Button
					fullWidth
					radius={radii.md}
					size="md"
					onClick={soonHandlers.close}
					styles={{
						root: {
							backgroundColor: "#1A73E8",
							"&:hover": { backgroundColor: "#1557B0" },
						},
					}}
				>
					{t("settings.gotIt")}
				</Button>
			</Drawer>



			{/* ─── Logout Confirmation ─── */}
			<Modal
				opened={logoutOpened}
				onClose={logoutHandlers.close}
				withCloseButton={false}
				centered
				radius={radii.md}
				padding="lg"
				size="sm"
				styles={{
					content: { margin: "0 16px" },
				}}
			>
				<Text
					ta="center"
					style={{
						fontSize: 17,
						fontWeight: 600,
						color: "#1C1C1E",
						marginBottom: 20,
					}}
				>
					{t("settings.logoutConfirm")}
				</Text>
				<Box
					style={{
						display: "flex",
						gap: 12,
					}}
				>
					<Button
						variant="default"
						radius={9999}
						size="md"
						onClick={logoutHandlers.close}
						style={{ flex: 1 }}
						styles={{
							root: {
								borderColor: "#E8E8ED",
								color: "#3C3C43",
							},
							label: {
								whiteSpace: "nowrap",
								overflow: "visible",
							},
						}}
					>
						{t("settings.cancel")}
					</Button>
					<Button
						radius={9999}
						size="md"
						onClick={handleLogout}
						style={{ flex: 1 }}
						styles={{
							root: {
								backgroundColor: "#FF3B30",
								"&:hover": { backgroundColor: "#E0322B" },
							},
							label: {
								whiteSpace: "nowrap",
								overflow: "visible",
							},
						}}
					>
						{t("settings.logout")}
					</Button>
				</Box>
			</Modal>

			{/* ─── Delete Account Confirmation ─── */}
			<Modal
				opened={deleteOpened}
				onClose={deleteHandlers.close}
				withCloseButton={false}
				centered
				radius={radii.md}
				padding="lg"
				size="sm"
				styles={{
					content: { margin: "0 16px" },
				}}
			>
				<Text
					ta="center"
					style={{
						fontSize: 17,
						fontWeight: 600,
						color: "#1C1C1E",
						marginBottom: 8,
					}}
				>
					{t("settings.deleteConfirmTitle")}
				</Text>
				<Text
					ta="center"
					style={{
						fontSize: 14,
						color: "#8E8E93",
						marginBottom: 20,
					}}
				>
					{t("settings.deleteConfirmMessage")}
				</Text>
				<Box
					style={{
						display: "flex",
						flexDirection: "column",
						gap: 10,
					}}
				>
					<Button
						fullWidth
						radius={9999}
						size="md"
						onClick={handleDelete}
						styles={{
							root: {
								backgroundColor: "#FF3B30",
								"&:hover": { backgroundColor: "#E0322B" },
							},
						}}
					>
						{t("settings.deleteAccount")}
					</Button>
					<Button
						fullWidth
						variant="default"
						radius={9999}
						size="md"
						onClick={deleteHandlers.close}
						styles={{
							root: {
								borderColor: "#E8E8ED",
								color: "#3C3C43",
							},
						}}
					>
						{t("settings.cancel")}
					</Button>
				</Box>
			</Modal>
		</RootPage>
	);
}

export const Settings = {
	route: "/settings",
	Page,
};
