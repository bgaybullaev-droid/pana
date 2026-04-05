import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useUnit } from "effector-react";
import { useTranslation } from "react-i18next";
import {
	Container,
	Stack,
	Text,
	Group,
	Box,
	Pagination,
	Skeleton,
	SimpleGrid,
	Card,
	ThemeIcon,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import {
	IconWorldSearch,
	IconBrandTelegram,
	IconHome,
	IconSearch,
} from "@tabler/icons-react";
import { InnerPage } from "@shared/ui/InnerPage";
import { claimOlxListing } from "@shared/api/sellerCrawledListings";
import { EmptyState } from "@shared/ui/EmptyState";
import { PillTabs } from "@shared/ui/PillTabs";
import { OLXListingCard } from "../main/OLXListingCard";
import { TelegramListingCard } from "../main/TelegramListingCard";
import { radii, shadows, surface } from "@app/styles/theme";
import {
	pageOpened,
	tabChanged,
	pageChanged,
	resetState,
	$stats,
	$activeTab,
	$page,
	$olxListings,
	$telegramListings,
	$totalPages,
	$isLoading,
	$isStatsLoading,
	$error,
} from "../../model";

function Page() {
	const { t } = useTranslation("seller");
	const navigate = useNavigate();
	const [
		stats,
		activeTab,
		page,
		olxListings,
		telegramListings,
		totalPages,
		isLoading,
		isStatsLoading,
		error,
	] = useUnit([
		$stats,
		$activeTab,
		$page,
		$olxListings,
		$telegramListings,
		$totalPages,
		$isLoading,
		$isStatsLoading,
		$error,
	]);

	useEffect(() => {
		pageOpened();
		return () => resetState();
	}, []);

	const listings = activeTab === "olx" ? olxListings : telegramListings;
	const [claimingId, setClaimingId] = useState<string | null>(null);

	const handleClaimOlx = useCallback(
		async (olxId: string) => {
			if (claimingId) return;
			setClaimingId(olxId);
			try {
				const listing = await claimOlxListing(olxId);
				notifications.show({
					title: t("notifications.done"),
					message: t("listings.claimSuccess"),
					color: "green",
				});
				navigate(`/seller/edit/${listing.id}`);
			} catch (err: unknown) {
				const status = (err as { response?: { status?: number } })?.response
					?.status;
				if (status === 409) {
					notifications.show({
						title: t("listings.alreadyClaimed"),
						message: t("listings.alreadyClaimedMsg"),
						color: "yellow",
					});
					pageOpened();
				} else if (status === 429) {
					notifications.show({
						title: t("listings.claimLimitTitle"),
						message: t("listings.claimLimitMsg"),
						color: "red",
					});
				} else {
					notifications.show({
						title: t("notifications.error"),
						message: t("listings.claimError"),
						color: "red",
					});
				}
			} finally {
				setClaimingId(null);
			}
		},
		[claimingId, navigate, t],
	);

	const renderTabs = () => {
		const tabsData = [
			{ value: "olx", label: "OLX", count: stats?.olx_count || 0 },
			{
				value: "telegram",
				label: "Telegram",
				count: stats?.telegram_count || 0,
			},
		];
		return (
			<PillTabs
				tabs={tabsData}
				activeValue={activeTab}
				onChange={(val) => tabChanged(val as "olx" | "telegram")}
			/>
		);
	};

	return (
		<InnerPage title={t("crawled.title")} noPadding>
			<Container px="sm" py="md">
			<Stack gap={16}>

				{/* ── Modern Compact Header ── */}
				<Box style={{ animation: "fade-in 0.4s ease-out" }}>
					{/* ── Context Card (Compact Mobile) ── */}
					<Card
						radius={radii.md}
						p="sm"
						mb="sm"
						style={{
							background: "#f0f9ff",
							border: "1px solid #bae6fd",
							boxShadow: "none",
						}}
					>
						<Group wrap="nowrap" gap="sm">
							<ThemeIcon variant="light" color="blue" size={36} radius="md">
								<IconSearch size={18} />
							</ThemeIcon>
							<Box style={{ flex: 1 }}>
								<Text size="13px" fw={700} c="dark.9">
									{t("crawled.subtitle")}
								</Text>
								<Text size="11px" c="dimmed" mt={2} lh={1.3}>
									{t("crawled.description")}
								</Text>
							</Box>
						</Group>
					</Card>

					{/* ── Stats ── */}
					{isStatsLoading ? (
						<SimpleGrid cols={3} spacing="xs">
							{[1, 2, 3].map((i) => (
								<Skeleton key={i} height={60} radius={12} />
							))}
						</SimpleGrid>
					) : stats ? (
						<SimpleGrid cols={3} spacing="xs">
							<Card
								radius={radii.md}
								p="sm"
								style={{
									boxShadow: shadows.md,
									border: "1px solid #f1f5f9",
								}}
							>
								<ThemeIcon
									size={24}
									radius="sm"
									color="teal"
									variant="light"
									mb={4}
								>
									<IconWorldSearch size={14} />
								</ThemeIcon>
								<Text fw={800} size="16px" c="dark.9" lh={1}>
									{stats.olx_count}
								</Text>
								<Text size="10px" fw={600} c="dimmed">
									OLX
								</Text>
							</Card>
							<Card
								radius={radii.md}
								p="sm"
								style={{
									boxShadow: shadows.md,
									border: "1px solid #f1f5f9",
								}}
							>
								<ThemeIcon
									size={24}
									radius="sm"
									color="cyan"
									variant="light"
									mb={4}
								>
									<IconBrandTelegram size={14} />
								</ThemeIcon>
								<Text fw={800} size="16px" c="dark.9" lh={1}>
									{stats.telegram_count}
								</Text>
								<Text size="10px" fw={600} c="dimmed">
									Telegram
								</Text>
							</Card>
							<Card
								radius={radii.md}
								p="sm"
								style={{
									boxShadow: shadows.md,
									border: "1px solid #f1f5f9",
								}}
							>
								<ThemeIcon
									size={24}
									radius="sm"
									color="violet"
									variant="light"
									mb={4}
								>
									<IconHome size={14} />
								</ThemeIcon>
								<Text fw={800} size="16px" c="dark.9" lh={1}>
									{stats.total_count}
								</Text>
								<Text size="10px" fw={600} c="dimmed">
									{t("crawled.total")}
								</Text>
							</Card>
						</SimpleGrid>
					) : null}
				</Box>

				{/* ── Error State ── */}
				{error && (
					<Card
						radius={radii.md}
						p="xs"
						style={{ backgroundColor: "#fef2f2", border: "1px solid #fecaca" }}
					>
						<Text c="red.7" ta="center" size="12px" fw={500}>
							{t(error, { defaultValue: error })}
						</Text>
					</Card>
				)}

				{/* ── Pill-style filter chips inside a subtle card ── */}
				<Box style={{ animation: "fade-in-up 0.4s ease-out 0.05s both" }}>
					<Card
						radius={radii.md}
						p={4}
						style={{
							background: surface.card,
							border: "1px solid #f1f5f9",
							boxShadow: shadows.md,
						}}
					>
						{renderTabs()}
					</Card>
				</Box>

				{/* ── Listings ── */}
				<Box style={{ animation: "fade-in-up 0.4s ease-out 0.1s both" }}>
					{isLoading && listings.length === 0 ? (
						<Stack gap="xs">
							{[1, 2, 3, 4].map((i) => (
								<Skeleton key={i} height={100} radius={12} />
							))}
						</Stack>
					) : !isLoading && listings.length === 0 && !error ? (
						<Box mt="xl">
							<EmptyState
								icon={activeTab === "olx" ? IconWorldSearch : IconBrandTelegram}
								title={t("crawled.nothingFound")}
								description={
									activeTab === "olx"
										? t("crawled.emptyOLX")
										: t("crawled.emptyTelegram")
								}
							/>
						</Box>
					) : (
						<Stack gap="sm">
							{activeTab === "olx"
								? olxListings.map((listing) => (
										<Box
											key={listing.id}
											style={{
												boxShadow: shadows.sm,
												borderRadius: radii.md,
												backgroundColor: surface.card,
												border: "1px solid #f1f5f9",
											}}
										>
											<OLXListingCard
												listing={listing}
												onClaim={handleClaimOlx}
												isClaiming={claimingId === listing.id}
											/>
										</Box>
									))
								: telegramListings.map((listing) => (
										<Box
											key={listing.id}
											style={{
												boxShadow: shadows.sm,
												borderRadius: radii.md,
												backgroundColor: surface.card,
												border: "1px solid #f1f5f9",
											}}
										>
											<TelegramListingCard listing={listing} />
										</Box>
									))}
						</Stack>
					)}
				</Box>

				{/* ── Pagination ── */}
				{!isLoading && totalPages > 1 && (
					<Group justify="center" mt="md">
						<Pagination
							total={totalPages}
							value={page}
							onChange={pageChanged}
							size="xs"
							radius="xl"
						/>
					</Group>
				)}
			</Stack>
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
			</Container>
		</InnerPage>
	);
}

export const CrawledListings = {
	route: "/seller/crawled",
	Page,
};
