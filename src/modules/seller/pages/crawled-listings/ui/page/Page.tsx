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

// TODO: Remove mock data before production
const MOCK_OLX = [
	{
		id: "mock-olx-1", olx_id: "olx-1001", url: "https://olx.uz/1001",
		property_type: "apartment", listing_type: "sell", price: 85000, currency: "USD",
		rooms: 3, area_sqm: 78, floor: 4, total_floors: 9, district: "yunusobod",
		address: "ул. Абдуллы Кадыри, 12", description: "Евроремонт, раздельная планировка, встроенная кухня",
		amenities: ["internet", "ac"], contact_phone: "+998901234567", confidence: 0.95,
		images: ["https://picsum.photos/seed/olx1/400/300"], source: "olx.uz",
		crawled_at: new Date().toISOString(), seller_type: "owner", seller_name: "Алишер К.",
		views_count: 142, posted_date: new Date(Date.now() - 86400000 * 2).toISOString(),
		building_type: "new", condition: "euro", created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
	},
	{
		id: "mock-olx-2", olx_id: "olx-1002", url: "https://olx.uz/1002",
		property_type: "house", listing_type: "sell", price: 270000, currency: "USD",
		rooms: 6, area_sqm: 220, floor: null, total_floors: 2, district: "sergeli",
		address: "Сергелийский р-н", description: "Двухэтажный дом с участком 6 соток, бассейн, гараж",
		amenities: ["garage", "pool"], contact_phone: "+998931234567", confidence: 0.88,
		images: ["https://picsum.photos/seed/olx2/400/300"], source: "olx.uz",
		crawled_at: new Date(Date.now() - 3600000).toISOString(), seller_type: "realtor", seller_name: "Агентство Комфорт",
		views_count: 89, posted_date: new Date(Date.now() - 86400000).toISOString(),
		building_type: "secondary", condition: "cosmetic", created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
	},
	{
		id: "mock-olx-3", olx_id: "olx-1003", url: "https://olx.uz/1003",
		property_type: "land", listing_type: "sell", price: 45000, currency: "USD",
		rooms: null, area_sqm: 800, floor: null, total_floors: null, district: "yashnobod",
		address: "Яшнободский р-н", description: "Участок под строительство, коммуникации рядом",
		amenities: null, contact_phone: "+998951234567", confidence: 0.92,
		images: ["https://picsum.photos/seed/olx3/400/300"], source: "olx.uz",
		crawled_at: new Date(Date.now() - 7200000).toISOString(), seller_type: "owner", seller_name: null,
		views_count: 56, posted_date: new Date(Date.now() - 86400000 * 3).toISOString(),
		building_type: null, condition: null, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
	},
];

const MOCK_TELEGRAM = [
	{
		id: "mock-tg-1", property_type: "apartment", listing_type: "rent", price: 500, currency: "USD",
		rooms: 2, area_sqm: 65, floor: 7, total_floors: 12, district: "chilonzor",
		address: "Чиланзар, 10 квартал", description: "Квартира с мебелью и техникой, рядом метро",
		amenities: ["internet", "fridge", "washing_machine"], contact_phone: "+998901112233",
		confidence: 0.91, images: ["https://picsum.photos/seed/tg1/400/300"],
		raw_text: null, source_channel: "@tashkent_kvartiry", message_id: 12345, signature_hash: null,
		created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
	},
	{
		id: "mock-tg-2", property_type: "commercial", listing_type: "rent", price: 1200, currency: "USD",
		rooms: null, area_sqm: 120, floor: 1, total_floors: 5, district: "mirobod",
		address: "Мирабадский р-н, ул. Навои", description: "Помещение под офис или магазин, первая линия",
		amenities: ["ac"], contact_phone: "+998909998877",
		confidence: 0.85, images: ["https://picsum.photos/seed/tg2/400/300"],
		raw_text: null, source_channel: "@arenda_tashkent", message_id: 12346, signature_hash: null,
		created_at: new Date(Date.now() - 3600000).toISOString(), updated_at: new Date().toISOString(),
	},
];

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

	// TODO: Remove mock fallback before production
	const effectiveOlx = olxListings.length > 0 ? olxListings : (MOCK_OLX as typeof olxListings);
	const effectiveTelegram = telegramListings.length > 0 ? telegramListings : (MOCK_TELEGRAM as typeof telegramListings);
	const listings = activeTab === "olx" ? effectiveOlx : effectiveTelegram;
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
			<Container px="md" py="md">
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
								? effectiveOlx.map((listing) => (
										<OLXListingCard
											key={listing.id}
											listing={listing}
											onClaim={handleClaimOlx}
											isClaiming={claimingId === listing.id}
										/>
									))
								: effectiveTelegram.map((listing) => (
										<TelegramListingCard key={listing.id} listing={listing} />
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
