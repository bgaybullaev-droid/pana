import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Container,
	Stack,
	Text,
	SimpleGrid,
	Box,
	Skeleton,
	UnstyledButton,
	Group,
	Card,
	Avatar,
	ThemeIcon,
	Center,
	ActionIcon,
} from "@mantine/core";
import {
	IconPlus,
	IconList,
	IconEye,
	IconPhone,
	IconHeart,
	IconUser,
	IconWorldSearch,
	IconArrowRight,
	IconBuildingStore,
	IconSparkles,
} from "@tabler/icons-react";
import { InnerPage } from "@shared/ui/InnerPage";
import {
	$sellerProfile,
	$sellerStats,
	$isLoadingProfile,
	fetchSellerProfile,
} from "@modules/seller/shared/state";
import { radii, shadows, spacing, surface } from '@app/styles/theme';

function Page() {
	const navigate = useNavigate();
	const [sellerProfile, stats, isLoading] = useUnit([
		$sellerProfile,
		$sellerStats,
		$isLoadingProfile,
	]);
	const initializedRef = useRef(false);
	const { t } = useTranslation("seller");

	useEffect(() => {
		if (initializedRef.current) return;
		initializedRef.current = true;
		if (!sellerProfile && !isLoading) {
			fetchSellerProfile();
		}
	}, [sellerProfile, isLoading]);

	return (
		<InnerPage title={t("dashboard.title", "Dashboard")} noPadding>
			<Container px="md" py="md">
			<Stack gap={16}>

				{/* ── Greeting Card (Compact Mobile) ── */}
				<Box style={{ animation: 'fade-in 0.4s ease-out' }}>
					{isLoading ? (
						<Skeleton height={90} radius={16} />
					) : (
						<Group wrap="nowrap" gap="sm" align="center" style={{
							background: "linear-gradient(135deg, #228be6, #1864ab)",
							borderRadius: radii.lg,
							padding: spacing.card,
							boxShadow: shadows.accent,
						}}>
							<Avatar
								src={sellerProfile?.logo_url}
								size={48}
								radius={24}
								color="blue.7"
								style={{ border: "2px solid #fff", backgroundColor: "#fff" }}
							>
								{sellerProfile?.company_name?.[0]?.toUpperCase() || <IconBuildingStore size={22} />}
							</Avatar>
							<Box style={{ flex: 1 }}>
								<Text size="10px" c="rgba(255,255,255,0.8)" fw={700} tt="uppercase" style={{ letterSpacing: 0.5 }}>
									{t("dashboard.welcome", "WELCOME")}
								</Text>
								<Text size="18px" fw={700} c="white" lh={1.2} lineClamp={1}>
									{sellerProfile?.company_name || t("dashboard.seller", "Seller")}
								</Text>
							</Box>
						</Group>
					)}
				</Box>

				{/* ── Compact Stat Blocks ── */}
				<Box style={{ animation: 'fade-in-up 0.4s ease-out 0.05s both' }}>
					<Text fw={700} size="sm" c="dark.8" mb="xs">
						{t("dashboard.statsToday", "Overview")}
					</Text>
					<SimpleGrid cols={2} spacing="xs">
						{isLoading ? (
							<>
								<Skeleton height={80} radius={12} />
								<Skeleton height={80} radius={12} />
								<Skeleton height={80} radius={12} />
								<Skeleton height={80} radius={12} />
							</>
						) : (
							<>
								<Card radius={radii.md} p="sm" style={{ boxShadow: shadows.sm, border: '1px solid #f1f5f9' }}>
									<Group wrap="nowrap" align="center" gap="sm">
										<ThemeIcon size={32} radius="md" color="blue" variant="light">
											<IconList size={16} />
										</ThemeIcon>
										<Box>
											<Text fw={800} size="18px" c="dark.9" lh={1}>{stats?.totalListings ?? 0}</Text>
											<Text size="10px" fw={600} c="dimmed">{t("dashboard.listings", "Listings")}</Text>
										</Box>
									</Group>
								</Card>
								
								<Card radius={radii.md} p="sm" style={{ boxShadow: shadows.sm, border: '1px solid #f1f5f9' }}>
									<Group wrap="nowrap" align="center" gap="sm">
										<ThemeIcon size={32} radius="md" color="teal" variant="light">
											<IconEye size={16} />
										</ThemeIcon>
										<Box>
											<Text fw={800} size="18px" c="dark.9" lh={1}>{stats?.totalViews ?? 0}</Text>
											<Text size="10px" fw={600} c="dimmed">{t("dashboard.views", "Views")}</Text>
										</Box>
									</Group>
								</Card>

								<Card radius={radii.md} p="sm" style={{ boxShadow: shadows.sm, border: '1px solid #f1f5f9' }}>
									<Group wrap="nowrap" align="center" gap="sm">
										<ThemeIcon size={32} radius="md" color="orange" variant="light">
											<IconPhone size={16} />
										</ThemeIcon>
										<Box>
											<Text fw={800} size="18px" c="dark.9" lh={1}>{stats?.totalContacts ?? 0}</Text>
											<Text size="10px" fw={600} c="dimmed">{t("dashboard.contacts", "Contacts")}</Text>
										</Box>
									</Group>
								</Card>

								<Card radius={radii.md} p="sm" style={{ boxShadow: shadows.sm, border: '1px solid #f1f5f9' }}>
									<Group wrap="nowrap" align="center" gap="sm">
										<ThemeIcon size={32} radius="md" color="pink" variant="light">
											<IconHeart size={16} />
										</ThemeIcon>
										<Box>
											<Text fw={800} size="18px" c="dark.9" lh={1}>{stats?.totalFavorites ?? 0}</Text>
											<Text size="10px" fw={600} c="dimmed">{t("dashboard.favorites", "Favorites")}</Text>
										</Box>
									</Group>
								</Card>
							</>
						)}
					</SimpleGrid>
				</Box>

				{/* ── Quick Actions Grid (Compact list) ── */}
				<Box style={{ animation: 'fade-in-up 0.4s ease-out 0.1s both' }}>
					<Text fw={700} size="sm" mb="xs" c="dark.8">
						{t("dashboard.quickActions", "Actions")}
					</Text>
					<Stack gap="xs">
						<UnstyledButton onClick={() => navigate("/seller/create")}>
							<Card radius={radii.md} p="sm" style={{ background: '#228be6', color: 'white', border: 'none', boxShadow: shadows.accent }}>
								<Group wrap="nowrap" justify="space-between">
									<Group wrap="nowrap" gap="sm">
										<Center style={{ width: 32, height: 32, borderRadius: radii.sm, background: 'rgba(255,255,255,0.2)' }}>
											<IconPlus size={18} color="white" />
										</Center>
										<Text fw={600} size="13px">{t("dashboard.createListing", "Create Listing")}</Text>
									</Group>
									<IconArrowRight size={16} opacity={0.7} />
								</Group>
							</Card>
						</UnstyledButton>

						<UnstyledButton onClick={() => navigate("/seller/listings")}>
							<Card radius={radii.md} p="sm" style={{ background: surface.card, border: '1px solid #f1f5f9', boxShadow: shadows.sm }}>
								<Group wrap="nowrap" justify="space-between">
									<Group wrap="nowrap" gap="sm">
										<Center style={{ width: 32, height: 32, borderRadius: radii.sm, background: surface.page, color: '#475569' }}>
											<IconList size={18} />
										</Center>
										<Text fw={600} size="13px" c="dark.8">{t("dashboard.myListings", "My Listings")}</Text>
									</Group>
									<IconArrowRight size={16} color="#cbd5e1" />
								</Group>
							</Card>
						</UnstyledButton>

						<UnstyledButton onClick={() => navigate("/profile")}>
							<Card radius={radii.md} p="sm" style={{ background: surface.card, border: '1px solid #f1f5f9', boxShadow: shadows.sm }}>
								<Group wrap="nowrap" justify="space-between">
									<Group wrap="nowrap" gap="sm">
										<Center style={{ width: 32, height: 32, borderRadius: radii.sm, background: surface.page, color: '#475569' }}>
											<IconUser size={18} />
										</Center>
										<Text fw={600} size="13px" c="dark.8">{t("dashboard.profile", "Profile")}</Text>
									</Group>
									<IconArrowRight size={16} color="#cbd5e1" />
								</Group>
							</Card>
						</UnstyledButton>

						<UnstyledButton onClick={() => navigate("/seller/crawled")}>
							<Card radius={radii.md} p="sm" style={{ background: surface.card, border: '1px solid #f1f5f9', boxShadow: shadows.sm }}>
								<Group wrap="nowrap" justify="space-between">
									<Group wrap="nowrap" gap="sm">
										<Center style={{ width: 32, height: 32, borderRadius: radii.sm, background: surface.page, color: '#10b981' }}>
											<IconWorldSearch size={18} />
										</Center>
										<Text fw={600} size="13px" c="dark.8">{t("dashboard.found", "Found Listings")}</Text>
									</Group>
									<IconArrowRight size={16} color="#cbd5e1" />
								</Group>
							</Card>
						</UnstyledButton>
					</Stack>
				</Box>

				{/* ── Compact Onboarding Prompt ── */}
				{stats && stats.totalListings === 0 && !isLoading && (
					<Box style={{ animation: 'fade-in-up 0.4s ease-out 0.15s both' }}>
						<UnstyledButton onClick={() => navigate("/seller/create")} style={{ width: '100%', display: 'block' }}>
							<Card
								radius={radii.md}
								p="sm"
								style={{
									background: "#f0f9ff",
									border: "1px dashed #38bdf8",
									boxShadow: shadows.accent,
								}}
							>
								<Group wrap="nowrap" gap="sm" align="center">
									<ThemeIcon variant="light" color="blue" size={36} radius="md">
										<IconSparkles size={18} />
									</ThemeIcon>
									<Box style={{ flex: 1 }}>
										<Text size="13px" fw={700} c="dark.9">
											{t("dashboard.createFirst", "Add your first property")}
										</Text>
										<Text size="11px" c="dimmed" mt={2} lh={1.3} fw={500}>
											{t("dashboard.createFirstDescription", "Start managing your properties.")}
										</Text>
									</Box>
									<ActionIcon variant="light" color="blue" radius="md" size="sm">
										<IconArrowRight size={14} />
									</ActionIcon>
								</Group>
							</Card>
						</UnstyledButton>
					</Box>
				)}

				<style>{`
					@keyframes fade-in {
						from { opacity: 0; }
						to { opacity: 1; }
					}
					@keyframes fade-in-up {
						from { opacity: 0; transform: translateY(10px); }
						to { opacity: 1; transform: translateY(0); }
					}
				`}</style>
			</Stack>
			</Container>
		</InnerPage>
	);
}

export const SellerDashboard = {
	route: "/seller/dashboard",
	Page,
};
